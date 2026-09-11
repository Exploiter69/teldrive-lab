"""Launch the read-only local TelDrive Lab Control Center."""
from __future__ import annotations
import argparse
from teldrive_lab.advanced import control_center_server


def main() -> int:
    p=argparse.ArgumentParser(description='TelDrive Lab read-only control center')
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',type=int,default=8790)
    args=p.parse_args()
    server=control_center_server(host=args.host,port=args.port)
    print(f'TelDrive Lab Control Center: http://{args.host}:{args.port}/')
    print('Mutation API: NONE')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
