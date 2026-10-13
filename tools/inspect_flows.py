"""inspect_flows.py — 看抓包里 WS 升级握手的 HTTP 头（App 到底怎么连的）"""
import pathlib
import sys

from mitmproxy import io as mio


def main():
    paths = [pathlib.Path(x) for x in sys.argv[1:]] or sorted(
        pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm").glob("*.mitm"), key=lambda p: p.stat().st_mtime
    )
    for p in paths:
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if not flow.websocket:
                        continue
                    print(f"### {p.name} {flow.request.method} {flow.request.pretty_url}")
                    print(f"    HTTP {flow.request.http_version}  ->  {flow.response.status_code if flow.response else '?'}")
                    for k, v in flow.request.headers.items():
                        print(f"    REQ  {k}: {v[:150]}")
                    print()
                    raise SystemExit(0)
        except SystemExit:
            raise
        except Exception as e:
            print(f"[warn] {p.name}: {e}")


if __name__ == "__main__":
    main()
