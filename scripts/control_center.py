"""Launch the read-only local TelDrive Lab Control Center."""
from __future__ import annotations

import argparse

from teldrive_lab.control_center import control_center_server


def main() -> int:
    parser = argparse.ArgumentParser(description="TelDrive Lab read-only control center")
    parser.add_argument("--state-root", default=None, help="Lab-owned runtime state root")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8790)
    args = parser.parse_args()
    server = control_center_server(args.state_root, host=args.host, port=args.port)
    print(f"TelDrive Lab Control Center: http://{args.host}:{args.port}/")
    print("Mutation API: NONE")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
