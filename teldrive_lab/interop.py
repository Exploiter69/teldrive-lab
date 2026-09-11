"""Dependency-free read-only Unix-socket IPC for TelDrive Lab metadata."""
from __future__ import annotations
import json
import socketserver
from pathlib import Path
from typing import Callable, Any


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        line=self.rfile.readline(1_048_576)
        try: request=json.loads(line.decode())
        except Exception: self.wfile.write(b'{"ok":false,"error":"invalid_json"}\n'); return
        if request.get("op") not in {"health","metadata"}:
            self.wfile.write(b'{"ok":false,"error":"read_only"}\n'); return
        try: result=self.server.provider(request)  # type: ignore[attr-defined]
        except Exception as exc: result={"ok":False,"error":str(exc)}
        self.wfile.write((json.dumps(result,default=str)+"\n").encode())


def serve_ipc(socket_path: Path, provider: Callable[[dict[str,Any]],Any]):
    socket_path.parent.mkdir(parents=True,exist_ok=True)
    if socket_path.exists(): socket_path.unlink()
    class Server(socketserver.ThreadingUnixStreamServer):
        allow_reuse_address=True
    server=Server(str(socket_path),_Handler); server.provider=provider  # type: ignore[attr-defined]
    return server
