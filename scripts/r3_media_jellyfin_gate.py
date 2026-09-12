#!/usr/bin/env python3
"""R3 gate: real Docker Jellyfin + read-only media bind + real stream."""
from __future__ import annotations
import json, os, socket, tempfile, time, shutil
from pathlib import Path
from teldrive_lab.media_jellyfin import R3Error, add_library, configure_jellyfin, discover_filesystem, docker_run_jellyfin, docker_stop, find_item, make_fixture, verify_stream, wait_for_jellyfin, refresh_library

def free_port():
    with socket.socket() as s:s.bind(("127.0.0.1",0));return int(s.getsockname()[1])
def main():
    root=Path(tempfile.mkdtemp(prefix="teldrive-r3-"));media=root/"media";config=root/"config";cache=root/"cache"
    for p in (config,cache):p.mkdir()
    fixture=make_fixture(media);discovered=discover_filesystem(media);assert len(discovered)==1 and discovered[0].media_type=="audio","media discovery failed"
    port=free_port();base=f"http://127.0.0.1:{port}";container=None
    try:
        print("R3: starting official Jellyfin container",flush=True);container=docker_run_jellyfin(config,cache,media,port)
        print("R3: waiting for Jellyfin",flush=True);wait_for_jellyfin(base,90)
        print("R3: completing startup/auth",flush=True);token=configure_jellyfin(base)
        print("R3: adding Music library",flush=True);add_library(base,token,"R3 Music","/media/Music","music");refresh_library(base,token)
        item=None
        for _ in range(60):
            item=find_item(base,token,fixture.name)
            if item:break
            time.sleep(1)
        assert item and item.get("Id"),"Jellyfin did not index fixture"
        print("R3: reading real media stream",flush=True);stream=verify_stream(base,token,item["Id"])
        data=json.loads(os.popen(f"docker inspect {container}").read())[0];media_mount=next((m for m in data.get("Mounts",[]) if m.get("Destination")=="/media"),None)
        assert media_mount and media_mount.get("RW") is False,"Jellyfin media mount is not read-only"
        print("R3 MEDIA/JELLYFIN GATE: PASS");print("- media discovery: PASS");print("- real Jellyfin container: PASS");print("- read-only media mount: PASS");print("- library scan/index: PASS");print("- real media stream: PASS");print("- TelDrive production mutation: NONE");print(json.dumps({"item":item.get("Name"),"stream":stream,"container":container},indent=2,default=str));return 0
    except (AssertionError,R3Error) as exc:
        print(f"R3 MEDIA/JELLYFIN GATE: FAIL\n- {exc}",flush=True)
        if container:
            logs=os.popen(f"docker logs {container} 2>&1 | tail -80").read();print("--- JELLYFIN LOG TAIL ---\n"+logs,flush=True)
        return 1
    finally:
        if container:docker_stop(container)
        shutil.rmtree(root,ignore_errors=True)
if __name__=="__main__":raise SystemExit(main())
