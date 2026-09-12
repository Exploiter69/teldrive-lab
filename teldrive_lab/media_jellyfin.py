"""R3 media discovery, read-only exposure, and real Jellyfin verification."""
from __future__ import annotations
import json, os, shutil, signal, subprocess, time, urllib.error, urllib.parse, urllib.request, wave
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from .models import FileRecord
from .resources import DEFAULT_MAX_DEPTH, DEFAULT_MAX_FILES, iter_files
VIDEO={".mp4",".mkv",".webm",".mov",".avi",".m4v"}; AUDIO={".mp3",".flac",".wav",".m4a",".ogg",".opus",".aac"}; IMAGE={".jpg",".jpeg",".png",".webp",".gif"}; SUBTITLE={".srt",".vtt",".ass",".ssa"}
@dataclass(frozen=True, slots=True)
class MediaCandidate:
    catalog_id:int|None; source:str; source_path:str; media_type:str; container:str; size:int; modified_at:str|None; confidence:float
@dataclass(frozen=True, slots=True)
class MediaExposure:
    mount_path:str; mode:str; source:str; read_only:bool; pid:int|None=None
@dataclass(frozen=True, slots=True)
class JellyfinStatus:
    reachable:bool; server_name:str|None; version:str|None; base_url:str
class R3Error(RuntimeError): pass
def classify_path(path:Path):
    ext=path.suffix.lower()
    if ext in VIDEO:return("video",ext[1:],.99)
    if ext in AUDIO:return("audio",ext[1:],.99)
    if ext in IMAGE:return("image",ext[1:],.95)
    if ext in SUBTITLE:return("subtitle",ext[1:],.95)
    return None
def discover_media(records:list[FileRecord])->list[MediaCandidate]:
    out=[]
    for r in records:
        k=classify_path(Path(r.path))
        if k:out.append(MediaCandidate(r.id,r.source_identifier,r.path,k[0],k[1],r.size or 0,r.modified_at,k[2]))
    return out
def discover_filesystem(root:Path,*,source="LOCAL_FIXTURE",max_depth=DEFAULT_MAX_DEPTH,max_files=DEFAULT_MAX_FILES)->list[MediaCandidate]:
    out=[]
    for p in iter_files(root,max_depth=max_depth,max_files=max_files):
        k=classify_path(p)
        if not k:continue
        try:s=p.stat()
        except OSError:continue
        out.append(MediaCandidate(None,source,str(p),k[0],k[1],s.st_size,str(s.st_mtime),k[2]))
    return out
def validate_exposure(mount_path:Path,protected_roots:tuple[Path,...]=()):
    resolved=mount_path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():raise R3Error(f"media exposure path does not exist: {resolved}")
    for protected in protected_roots:
        p=protected.expanduser().resolve()
        if resolved==p or p in resolved.parents or resolved in p.parents:raise R3Error("media exposure overlaps a protected production root")
def rclone_mount_command(remote:str,mount_path:Path)->list[str]:
    if not remote or remote.startswith("/"):raise R3Error("R3 TelDrive exposure requires a named rclone remote")
    return ["rclone","mount",remote,str(mount_path),"--read-only","--vfs-cache-mode","off","--dir-cache-time","10s","--poll-interval","30s"]
def start_rclone_exposure(remote:str,mount_path:Path,*,timeout=20)->MediaExposure:
    validate_exposure(mount_path);mount_path.mkdir(parents=True,exist_ok=True);proc=subprocess.Popen(rclone_mount_command(remote,mount_path),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,start_new_session=True);deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if proc.poll() is not None:raise R3Error(f"rclone mount exited: {(proc.stderr.read() if proc.stderr else '')[-1000:]}")
        if any(mount_path.iterdir()):return MediaExposure(str(mount_path),"RCLONE_READ_ONLY",remote,True,proc.pid)
        time.sleep(.25)
    os.killpg(proc.pid,signal.SIGTERM);raise R3Error("rclone read-only mount did not become visible before timeout")
def stop_exposure(exposure:MediaExposure):
    if exposure.pid:
        try:os.killpg(exposure.pid,signal.SIGTERM)
        except ProcessLookupError:pass
def _request(base_url,path,*,method="GET",token=None,payload=None,timeout=10):
    data=None if payload is None else json.dumps(payload).encode();headers={"Accept":"application/json","Content-Type":"application/json"}
    if token:headers["X-Emby-Token"]=token
    req=urllib.request.Request(base_url.rstrip("/")+path,data=data,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as response:
            raw=response.read()
            if not raw:return response.status,None
            try:return response.status,json.loads(raw.decode())
            except json.JSONDecodeError:return response.status,raw
    except urllib.error.HTTPError as exc:raise R3Error(f"Jellyfin HTTP {exc.code}: {exc.read().decode(errors='replace')[:500]}") from exc
    except urllib.error.URLError as exc:raise R3Error(f"Jellyfin unreachable: {exc.reason}") from exc
def jellyfin_status(base_url="http://127.0.0.1:8096"):
    try:
        _,d=_request(base_url,"/System/Info/Public",timeout=3);return JellyfinStatus(True,d.get("ServerName"),d.get("Version"),base_url)
    except R3Error:return JellyfinStatus(False,None,None,base_url)
def wait_for_jellyfin(base_url,timeout=90):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        s=jellyfin_status(base_url)
        if s.reachable:return s
        time.sleep(1)
    raise R3Error("Jellyfin did not become ready")
def configure_jellyfin(base_url,username="r3-admin",password="r3-pass"):
    for path,payload in [("/Startup/Configuration",{"UICulture":"en-US","MetadataCountryCode":"US","PreferredMetadataLanguage":"en"}),("/Startup/User",{"Name":username,"Password":password}),("/Startup/RemoteAccess",{"EnableRemoteAccess":False,"EnableAutomaticPortMapping":False}),("/Startup/Complete",{})]:
        try:_request(base_url,path,method="POST",payload=payload)
        except R3Error as exc:
            if "HTTP 401" not in str(exc) and "HTTP 400" not in str(exc):raise
    _,auth=_request(base_url,"/Users/AuthenticateByName",method="POST",payload={"Username":username,"Pw":password})
    token=auth.get("AccessToken") if isinstance(auth,dict) else None
    if not token:raise R3Error("Jellyfin authentication returned no access token")
    return token
def add_library(base_url,token,name,path,collection_type="music"):
    query=urllib.parse.urlencode({"name":name,"collectionType":collection_type,"paths":path,"refreshLibrary":"true"})
    body={"LibraryOptions":{"PathInfos":[{"Path":path}]}}
    try:_request(base_url,"/Library/VirtualFolders?"+query,method="POST",token=token,payload=body)
    except R3Error as exc:
        if "HTTP 409" not in str(exc):raise
def refresh_library(base_url,token):_request(base_url,"/Library/Refresh",method="POST",token=token,payload=None)
def library_items(base_url,token,search_term=""):
    query={"Recursive":"true","Limit":"100"}
    if search_term:query["SearchTerm"]=search_term
    _,data=_request(base_url,"/Items?"+urllib.parse.urlencode(query),token=token);return list(data.get("Items",[])) if isinstance(data,dict) else []
def find_item(base_url,token,name):
    stem=Path(name).stem
    for item in library_items(base_url,token,stem):
        if item.get("Name") in {name,stem} or Path(item.get("Path","")).name in {name,stem} or Path(item.get("Path","")).stem==stem:return item
    return None
def verify_stream(base_url,token,item_id,timeout=20):
    for endpoint in (f"/Audio/{item_id}/stream?static=true",f"/Items/{item_id}/Download"):
        try:
            req=urllib.request.Request(base_url.rstrip("/")+endpoint,headers={"X-Emby-Token":token})
            with urllib.request.urlopen(req,timeout=timeout) as response:
                chunk=response.read(4096)
                if chunk:return {"ok":True,"status":response.status,"bytes_sampled":len(chunk),"endpoint":endpoint}
        except Exception:continue
    raise R3Error("Jellyfin exposed the item but no media stream could be read")
def make_fixture(root:Path)->Path:
    music=root/"Music";music.mkdir(parents=True,exist_ok=True);wav=music/"R3 Test Tone.wav"
    with wave.open(str(wav),"wb") as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(8000)
        import math,struct
        out.writeframes(b"".join(struct.pack("<h",int(12000*math.sin(2*math.pi*440*t/8000))) for t in range(8000)))
    return wav
def docker_run_jellyfin(config:Path,cache:Path,media:Path,port:int)->str:
    if shutil.which("docker") is None:raise R3Error("docker is required for the real Jellyfin R3 gate")
    name=f"teldrive-r3-{os.getpid()}";command=["docker","run","-d","--rm","--name",name,"-p",f"127.0.0.1:{port}:8096","--mount",f"type=bind,source={config},target=/config","--mount",f"type=bind,source={cache},target=/cache","--mount",f"type=bind,source={media},target=/media,readonly","jellyfin/jellyfin:latest"]
    proc=subprocess.run(command,capture_output=True,text=True,check=False,timeout=120)
    if proc.returncode:raise R3Error(proc.stderr[-2000:])
    return name
def docker_stop(name):subprocess.run(["docker","rm","-f",name],capture_output=True,text=True,check=False,timeout=30)
def status_payload(base_url="http://127.0.0.1:8096"):
    status=jellyfin_status(base_url);return asdict(status)|{"exposure_policy":"READ_ONLY","telldrive_mutation":"NONE"}
