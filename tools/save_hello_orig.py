"""save_hello_orig.py — 把抓包里最后一条握手帧原样存成 hello_orig.bin（用于逐字节对比）"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from mitmproxy import io as mio  # noqa: E402

OUT = pathlib.Path(r"<WORKDIR>\artifacts\mitm\hello_orig.bin")


def main():
    paths = [pathlib.Path(x) for x in sys.argv[1:]] or sorted(
        pathlib.Path(r"<WORKDIR>\artifacts\mitm").glob("*.mitm"), key=lambda p: p.stat().st_mtime
    )
    last = None
    for p in paths:
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if not flow.websocket:
                        continue
                    for m in flow.websocket.messages:
                        raw = bytes(m.content)
                        if m.from_client and raw[:5] == b"\xf0\x04\x00\x01\x25":
                            last = raw
        except Exception as e:
            print(f"[warn] {p.name}: {e}")
    if not last:
        print("[FAIL] no handshake frame")
        return 1
    OUT.write_bytes(last)
    print(f"[OK] saved {len(last)} bytes -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
