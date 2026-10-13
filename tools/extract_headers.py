"""extract_headers.py — 从最新抓包里抽出某个接口的完整请求头，存成 JSON 复用

用法: python tools\\extract_headers.py write_off_card
"""
import json
import pathlib
import sys

from mitmproxy import io as mio

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")
SKIP = {"content-length", "accept-encoding", "host", ":authority", "x-request-start",
        "x-b3-spanid", "x-b3-traceid", "x-b3-sampled"}


def main():
    kw = sys.argv[1] if len(sys.argv) > 1 else "vip_experience_card"
    out = ROOT / f"headers_{kw.replace('/', '_')}.json"
    best = None
    for p in sorted(ROOT.glob("*.mitm"), key=lambda x: x.stat().st_mtime):
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if kw not in flow.request.pretty_url:
                        continue
                    hdr = {k: v for k, v in flow.request.headers.items() if k.lower() not in SKIP}
                    body = flow.request.get_text(strict=False) or ""
                    best = {"url": flow.request.pretty_url.split("?")[0], "headers": hdr, "body": body}
        except Exception as e:
            print(f"[warn] {p.name}: {e}")
    if not best:
        print("[FAIL] 没找到")
        return 1
    out.write_text(json.dumps(best, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] -> {out}")
    print(f"  url = {best['url']}")
    for k, v in best["headers"].items():
        print(f"  {k}: {v[:70]}")
    print(f"  body = {best['body'][:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
