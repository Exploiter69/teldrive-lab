#!/usr/bin/env python3
"""R3 gate: real Docker Jellyfin + read-only media bind + real stream."""
from __future__ import annotations
import json, os, socket, tempfile
from pathlib import Path
from teldrive_lab.media_jellyfin import R3Error, add_library, configure_jellyfin, discover_filesystem, docker_run_jellyfin, docker_stop, find_item, make_fixture, verify_stream, wait_for_jellyfin

def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1",0)); return int(s.getsockname()[1])

def main() -> int:
    root=Path(tempfile.mkdtemp(prefix="teldrive-r3-")); media=root/"media"; config=root/"config"; cache=root/"cache"
    for p in (config,cache):p.mkdir()
    fixture=make_fixture(media); discovered=discover_filesystem(media)
    assert len(discovered)==1 and discovered[0].media_type=="audio", "media discovery failed"
    port=free_port(); base=f"http://127.0.0.1:{port}"; container=None
    try:
        container=docker_run_jellyfin(config,cache,media,port)
        wait_for_jellyfin(base,90)
        token=configure_jellyfin(base)
        add_library(base,token,"R3 Music","/media/Music","music")
        # The library scan is requested by add_library; explicitly refresh once for deterministic verification.
        from teldrive_lab.media_jellyfin import refresh_library
        refresh_library(base,token)
        item=None
        for _ in range(60):
            item=find_item(base,token,fixture.name)
            if item:break
            import time;time.sleep(1)
        assert item and item.get("Id"), "Jellyfin did not index fixture"
        stream=verify_stream(base,token,item["Id"])
        inspect=os.popen(f"docker inspect {container}").read(); data=json.loads(inspect)[0]
        mounts=data.get("Mounts",[]); media_mount=next((m for m in mounts if m.get("Destination")=="/media"),None)
        assert media_mount and media_mount.get("RW") is False, "Jellyfin media mount is not read-only"
        print("R3 MEDIA/JELLYFIN GATE: PASS")
        print("- media discovery: PASS")
        print("- real Jellyfin container: PASS")
        print("- read-only media mount: PASS")
        print("- library scan/index: PASS")
        print("- real media stream: PASS")
        print("- TelDrive production mutation: NONE")
        print(json.dumps({"item":item.get("Name"),"stream":stream,"container":container},indent=2,default=str))
        return 0
    except (AssertionError,R3Error) as exc:
        print(f"R3 MEDIA/JELLYFIN GATE: FAIL\n- {exc}"); return 1
    finally:
        if container: docker_stop(container)
        import shutil; shutil.rmtree(root,ignore_errors=True)
if __name__=="__main__":raise SystemExit(main())
