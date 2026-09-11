"""Launch the dependency-free read-only metadata API."""
from __future__ import annotations
import argparse
from teldrive_lab.advanced import filesystem_metadata_view, serve_json_api
from pathlib import Path


def main() -> int:
    p=argparse.ArgumentParser(description='TelDrive Lab read-only metadata API')
    p.add_argument('--root',required=True)
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',type=int,default=8787)
    args=p.parse_args()
    root=Path(args.root).resolve()
    server=serve_json_api(lambda: filesystem_metadata_view(root),host=args.host,port=args.port)
    print(f'TelDrive Lab read-only API: http://{args.host}:{args.port}/health')
    print('POST/PUT/DELETE: disabled')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
