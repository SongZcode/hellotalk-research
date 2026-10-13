"""ht_obf.py — 解析「小帧」里的 obfuscated zlib：body 前 4 字节被变换过，需要还原

思路：对 41 字节上行帧，已知明文中包含 "last_id"（因为 {"last_id":0}），
尝试与已知明文做 XOR 求 key，验证同一 key 是否适用于其它帧。

用法: python tools\ht_obf.py artifacts\mitm\flows2.mitm
"""
import pathlib
import sys
import zlib

from mitmproxy import io as mio

PLAIN = b'{"last_id":0}'


def try_fix(body: bytes):
    """返回 (key, 修复后的 zlib 流) 列表"""
    out = []
    if len(body) < 8:
        return out
    head = body[:4]
    rest = body[4:]
    # 假设 zlib 头固定 78 9c，与 head 做 XOR 得 key
    key = bytes(a ^ b for a, b in zip(head[:2], b"\x78\x9c"))
    cand = key + rest if len(key) == 2 else None
    if cand:
        # key 只还原了 2 字节，剩下 2 字节用「明文前缀」推
        for pfx in (b"\x4b", b"\xab", b"\x4a", b"\x23"):
            c2 = pfx + rest
            try:
                d = zlib.decompressobj()
                txt = d.decompress(c2) + d.flush()
                if txt.startswith(b"{"):
                    out.append(("zlib-with-first-byte=" + pfx.hex(), txt))
                    break
            except zlib.error:
                pass
    return out


def brute_force(body: bytes, want: bytes):
    """暴力：设 body = X + zlib流，X 长度 4，用 4 字节 key 异或后解压，要求明文以 want 开头"""
    got = []
    for klen in (1, 2, 4):
        for candidate in range(0, 256**min(klen, 2)):
            pass
    return got


def main():
    for p in [pathlib.Path(x) for x in sys.argv[1:]]:
        if not p.exists():
            continue
        print(f"##### {p.name}")
        with open(p, "rb") as fh:
            frames = []
            for flow in mio.FlowReader(fh).stream():
                if not flow.websocket:
                    continue
                for m in flow.websocket.messages:
                    frames.append((m.from_client, bytes(m.content)))
        for i, (up, raw) in enumerate(frames):
            if len(raw) < 28:
                continue
            body = raw[24:]
            # 小帧特征：body 开头 78 9c，但第 3-6 字节与标准 zlib 不符
            if body[:2] != b"\x78\x9c":
                continue
            try:
                txt = zlib.decompressobj().decompress(body)
                continue  # 可正常解压，不处理
            except zlib.error:
                pass
            print(f"\n[{i}] {'UP' if up else 'DN'} body={body.hex()}")
            print(f"    head4={body[:4].hex()} rest={body[4:].hex()}")
            for name, cand in try_fix(body):
                print(f"    FIXED[{name}]: {cand[:120]!r}")


if __name__ == "__main__":
    main()
