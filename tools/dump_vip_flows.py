"""dump_vip_flows.py — 把 vip 相关接口的完整请求/响应（含 body 长度与内容）导成文件"""
import gzip
import pathlib
import zlib
import sys

from mitmproxy import io as mio

ROOT = pathlib.Path(r"<WORKDIR>\artifacts\mitm")
KEYS = ("payment_gateway", "vip_status_report", "vip_trial", "vip_product", "vip_page",
        "vip_banner", "user_virtual_info", "get_pay_chat_info", "act_preload_products")


def body_text(msg) -> str:
    try:
        raw = msg.get_content(strict=False)
    except Exception:
        raw = msg.content
    if isinstance(raw, str):
        return raw
    for fn in (gzip.decompress, lambda b: zlib.decompressobj().decompress(b)):
        try:
            out = fn(raw)
            if out:
                return out.decode("utf-8", "replace")
        except Exception:
            pass
    printable = sum(1 for c in raw[:200] if 32 <= c < 127) / max(1, len(raw[:200]))
    return raw.decode("utf-8", "replace") if printable > 0.85 else f"[binary {len(raw)}B] {raw[:64].hex()}"


def main():
    dump = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "flows_https.mitm"
    lines = []
    with open(dump, "rb") as fh:
        for flow in mio.FlowReader(fh).stream():
            url = flow.request.pretty_url
            if not any(k in url for k in KEYS):
                continue
            lines.append("=" * 100)
            lines.append(f"{flow.request.method} {url}")
            rb = body_text(flow.request).strip()
            lines.append(f"[REQ ] {rb[:600]}")
            if flow.response:
                lines.append(f"[RESP {flow.response.status_code}] {body_text(flow.response)[:1200]}")
            else:
                lines.append("[RESP] (none)")
    out = ROOT / "vip_flows.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] {len(lines)} 行 -> {out}")
    print("\n".join(lines)[:6000])


if __name__ == "__main__":
    main()
