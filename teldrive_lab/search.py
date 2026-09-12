"""Unified, read-only catalog search for TelDrive Lab."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime

from .catalog import Catalog
from .models import FileRecord, SourceType

MAX_LIMIT = 500
MAX_QUERY_LENGTH = 512
MAX_CONTENT_CHARS = 2_000_000

@dataclass(frozen=True, slots=True)
class SearchQuery:
    text: str = ""
    source_type: SourceType | None = None
    source_identifier: str | None = None
    extension: str | None = None
    mime_type: str | None = None
    path_prefix: str | None = None
    tag: str | None = None
    min_size: int | None = None
    max_size: int | None = None
    modified_after: str | None = None
    modified_before: str | None = None
    sort: str = "relevance"
    descending: bool = True
    limit: int = 50
    offset: int = 0

@dataclass(frozen=True, slots=True)
class SearchHit:
    record: FileRecord
    score: float

@dataclass(frozen=True, slots=True)
class SearchPage:
    query: SearchQuery
    hits: tuple[SearchHit, ...]
    total: int
    index_rebuilt: bool

class SearchError(ValueError):
    pass

class UnifiedSearch:
    """FTS5-backed unified search over metadata plus optional content indexes."""
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog
        self.db_path = catalog.path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            try:
                columns = connection.execute("PRAGMA table_info(r2_search_fts)").fetchall()
                if columns and "content" not in {row[1] for row in columns}:
                    connection.execute("DROP TABLE r2_search_fts")
                connection.execute("CREATE VIRTUAL TABLE IF NOT EXISTS r2_search_fts USING fts5(record_id UNINDEXED, path, name, parent_path, extension, mime_type, source_identifier, tags, content)")
            except sqlite3.OperationalError as exc:
                raise SearchError("SQLite FTS5 is required for R2 unified search") from exc
            connection.execute("CREATE TABLE IF NOT EXISTS r2_search_content (record_id INTEGER PRIMARY KEY, kind TEXT NOT NULL, content TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS r2_search_state (id INTEGER PRIMARY KEY CHECK(id=1), row_count INTEGER NOT NULL, max_last_seen TEXT, max_modified TEXT, content_count INTEGER NOT NULL)")
            connection.commit()

    @staticmethod
    def _fingerprint(connection: sqlite3.Connection) -> tuple[int, str | None, str | None, int]:
        row = connection.execute("SELECT COUNT(*) AS count, MAX(last_seen_at) AS last_seen, MAX(modified_at) AS modified FROM files").fetchone()
        content_count = int(connection.execute("SELECT COUNT(*) FROM r2_search_content").fetchone()[0])
        return int(row["count"]), row["last_seen"], row["modified"], content_count

    def rebuild(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM r2_search_fts")
            rows = connection.execute("SELECT f.id,f.path,f.name,f.parent_path,f.extension,f.mime_type,f.source_identifier,f.tags,COALESCE(c.content,'') FROM files f LEFT JOIN r2_search_content c ON c.record_id=f.id ORDER BY f.id").fetchall()
            connection.executemany("INSERT INTO r2_search_fts(record_id,path,name,parent_path,extension,mime_type,source_identifier,tags,content) VALUES (?,?,?,?,?,?,?,?,?)", [tuple(row) for row in rows])
            count, last_seen, modified, content_count = self._fingerprint(connection)
            connection.execute("DELETE FROM r2_search_state")
            connection.execute("INSERT INTO r2_search_state(id,row_count,max_last_seen,max_modified,content_count) VALUES(1,?,?,?,?)", (count, last_seen, modified, content_count))
            connection.commit()

    def ensure_current(self) -> bool:
        with self._connect() as connection:
            count, last_seen, modified, content_count = self._fingerprint(connection)
            state = connection.execute("SELECT row_count,max_last_seen,max_modified,content_count FROM r2_search_state WHERE id=1").fetchone()
            current = state is not None and int(state["row_count"]) == count and state["max_last_seen"] == last_seen and state["max_modified"] == modified and int(state["content_count"]) == content_count
        if current:
            return False
        self.rebuild()
        return True

    def index_content(self, record_id: int, content: str, *, kind: str = "text") -> None:
        if record_id < 1: raise SearchError("record_id must be positive")
        if len(content) > MAX_CONTENT_CHARS: raise SearchError(f"content exceeds {MAX_CONTENT_CHARS} characters")
        if not kind or len(kind) > 64: raise SearchError("content kind must be 1-64 characters")
        with self._connect() as connection:
            exists = connection.execute("SELECT 1 FROM files WHERE id=?", (record_id,)).fetchone()
            if exists is None: raise SearchError(f"catalog record not found: {record_id}")
            connection.execute("INSERT INTO r2_search_content(record_id,kind,content) VALUES(?,?,?) ON CONFLICT(record_id) DO UPDATE SET kind=excluded.kind,content=excluded.content", (record_id, kind, content))
            connection.commit()
        self.rebuild()

    def remove_content(self, record_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM r2_search_content WHERE record_id=?", (record_id,))
            connection.commit()
        self.rebuild()

    def search(self, query: SearchQuery | str) -> SearchPage:
        parsed = parse_query(query) if isinstance(query, str) else query
        _validate_query(parsed)
        rebuilt = self.ensure_current()
        with self._connect() as connection:
            where: list[str] = []
            params: list[object] = []
            join = ""
            order = "f.path COLLATE NOCASE ASC"
            if parsed.text:
                join = "JOIN r2_search_fts s ON s.record_id = f.id"
                where.append("s.r2_search_fts MATCH ?")
                params.append(_fts_match(parsed.text))
                order = "bm25(r2_search_fts) ASC, f.path COLLATE NOCASE ASC"
            if parsed.source_type: where.append("f.source_type=?"); params.append(parsed.source_type.value)
            if parsed.source_identifier: where.append("f.source_identifier=?"); params.append(parsed.source_identifier)
            if parsed.extension: where.append("f.extension=?"); params.append(_extension(parsed.extension))
            if parsed.mime_type:
                if "/" not in parsed.mime_type and not parsed.mime_type.startswith("."):
                    where.append("f.mime_type LIKE ?"); params.append(parsed.mime_type + "/%")
                else:
                    where.append("f.mime_type=?"); params.append(parsed.mime_type)
            if parsed.path_prefix:
                prefix = parsed.path_prefix.rstrip("/")
                where.append("(f.path=? OR f.path LIKE ?)"); params.extend([prefix, prefix + "/%"])
            if parsed.tag: where.append("COALESCE(f.tags,'') LIKE ? ESCAPE '\\'"); params.append('%"' + _like_escape(parsed.tag) + '"%')
            if parsed.min_size is not None: where.append("f.size>=?"); params.append(parsed.min_size)
            if parsed.max_size is not None: where.append("f.size<=?"); params.append(parsed.max_size)
            if parsed.modified_after: where.append("f.modified_at>=?"); params.append(parsed.modified_after)
            if parsed.modified_before: where.append("f.modified_at<=?"); params.append(parsed.modified_before)
            clause = " WHERE " + " AND ".join(where) if where else ""
            total = int(connection.execute("SELECT COUNT(*) FROM files f " + join + clause, params).fetchone()[0])
            if parsed.sort != "relevance": order = _sort_sql(parsed.sort, parsed.descending)
            elif not parsed.text: order = "f.path COLLATE NOCASE " + ("DESC" if parsed.descending else "ASC")
            rows = connection.execute("SELECT f.* FROM files f " + join + clause + " ORDER BY " + order + " LIMIT ? OFFSET ?", [*params, parsed.limit, parsed.offset]).fetchall()
            return SearchPage(parsed, tuple(SearchHit(FileRecord.from_mapping(row), 1.0) for row in rows), total, rebuilt)

def parse_query(value: str) -> SearchQuery:
    value = value.strip()
    if len(value) > MAX_QUERY_LENGTH: raise SearchError(f"query exceeds {MAX_QUERY_LENGTH} characters")
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|\S+', value)
    fields: dict[str, object] = {"text": []}
    names = {"source","source_id","ext","extension","mime","type","path","tag","min_size","max_size","after","before","sort","order","limit","offset"}
    for token in tokens:
        raw = token[1:-1] if len(token) >= 2 and token[0] == token[-1] == '"' else token
        if ":" not in raw or raw.split(":",1)[0].lower() not in names:
            fields["text"].append(raw); continue
        key, val = raw.split(":",1); key = key.lower(); val = val.strip()
        if not val: raise SearchError(f"empty value for {key}")
        if key == "source": fields["source_type"] = _source(val)
        elif key == "source_id": fields["source_identifier"] = val
        elif key in {"ext","extension"}: fields["extension"] = _extension(val)
        elif key in {"mime","type"}: fields["mime_type"] = val
        elif key == "path": fields["path_prefix"] = val
        elif key == "tag": fields["tag"] = val
        elif key == "min_size": fields["min_size"] = parse_size(val)
        elif key == "max_size": fields["max_size"] = parse_size(val)
        elif key == "after": fields["modified_after"] = _timestamp(val)
        elif key == "before": fields["modified_before"] = _timestamp(val)
        elif key == "sort": fields["sort"] = val.lower()
        elif key == "order": fields["descending"] = val.lower() in {"desc","descending","down"}
        elif key == "limit": fields["limit"] = int(val)
        elif key == "offset": fields["offset"] = int(val)
    fields["text"] = " ".join(fields["text"])
    return SearchQuery(**fields)

def parse_size(value: str) -> int:
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(b|kb|mb|gb|tb)?", value.strip(), re.I)
    if not match: raise SearchError(f"invalid size: {value}")
    return int(float(match.group(1)) * {"b":1,"kb":1024,"mb":1024**2,"gb":1024**3,"tb":1024**4}[(match.group(2) or "b").lower()])

def _source(value: str) -> SourceType:
    try: return SourceType(value.upper())
    except ValueError as exc: raise SearchError(f"unknown source type: {value}") from exc

def _extension(value: str) -> str:
    value = value.lower().strip(); return value if value.startswith(".") else "." + value

def _timestamp(value: str) -> str:
    try: return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError as exc: raise SearchError(f"invalid timestamp: {value}") from exc

def _fts_match(text: str) -> str:
    terms = re.findall(r"[\w.-]+", text, re.UNICODE)
    if not terms: raise SearchError("search text contains no searchable terms")
    return " AND ".join('"' + term.replace('"','""') + '"' for term in terms)

def _like_escape(value: str) -> str:
    return value.replace("%","\\%").replace("_","\\_")

def _sort_sql(sort: str, descending: bool) -> str:
    columns = {"path":"f.path","name":"f.name","size":"f.size","modified":"f.modified_at","created":"f.created_at","source":"f.source_type"}
    if sort not in columns: raise SearchError(f"unsupported sort: {sort}")
    return columns[sort] + (" DESC" if descending else " ASC") + ", f.path COLLATE NOCASE ASC"

def _validate_query(query: SearchQuery) -> None:
    if query.limit < 1 or query.limit > MAX_LIMIT: raise SearchError(f"limit must be between 1 and {MAX_LIMIT}")
    if query.offset < 0: raise SearchError("offset must be non-negative")
    if query.min_size is not None and query.max_size is not None and query.min_size > query.max_size: raise SearchError("min_size cannot exceed max_size")
    if query.sort not in {"relevance","path","name","size","modified","created","source"}: raise SearchError(f"unsupported sort: {query.sort}")

def search_catalog(catalog: Catalog, query: SearchQuery | str) -> SearchPage:
    return UnifiedSearch(catalog).search(query)
