"""brute_f5.py — 暴力尝试解开 f5 推送帧（0161/0361）的编码

已知：body 20/60 字节，前 4 字节固定 cdb7d2ce，尾部有变化。
试：raw deflate / zlib / gzip / lz4 / zstd，各自尝试不同起点偏移与 wbits。
"""
import pathlib
import sys
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import ht_frame as HF  # noqa: E402

ROOT = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm")
SAMPLES = [
    ("0161", bytes.fromhex("cdb7d2cefd3cb5501512dad093fdf5b9aa992b57"), 20),
    ("0361", bytes.fromhex("cdb7d2cee812c55bd4d1298ce4df5a269297088f048bbc6428064b5902124cbbb2ce407e5272f5e22d01fbe26626b98b98be637b503db31b2aceb659"), 60),
]


def try_codecs(data: bytes, off: int):
    out = []
    chunk = data[off:]
    for name, fn in (
        ("raw-deflate(-15)", lambda b: zlib.decompressobj(-15).decompress(b)),
        ("zlib(15)", lambda b: zlib.decompressobj(15).decompress(b)),
        ("gzip(31)", lambda b: zlib.decompressobj(31).decompress(b)),
    ):
        try:
            r = fn(chunk)
            if r:
                out.append((name, r))
        except Exception:
            pass
    return out


def xor_prefix_pattern(data: bytes):
    """打印与前 4 字节 cdb7d2ce 异或后的样子（看是否是已知魔数）"""
    return bytes(a ^ b for a, b in zip(data[:4], bytes.fromhex("cdb7d2ce"))).hex()


def main():
    # 收集更多样本
    from mitmproxy import io as mio

    samples = {}
    for p in sorted(ROOT.glob("*.mitm")):
        try:
            with open(p, "rb") as fh:
                for flow in mio.FlowReader(fh).stream():
                    if not flow.websocket:
                        continue
                    for m in flow.websocket.messages:
                        raw = bytes(m.content)
                        if raw[:3] == b"\xf5\x04\x01":
                            body = raw[20:]
                            samples.setdefault(f"{raw[4]:02x}{raw[5]:02x}:{len(body)}", body)
        except Exception as e:
            print(f"[warn] {p.name}: {e}")

    print(f"共 {len(samples)} 种 f5 帧形态:")
    for key, body in sorted(samples.items()):
        print(f"  {key}  {body[:24].hex()}{'...' if len(body) > 24 else ''}")

    for name, body, _ in SAMPLES:
        print(f"\n===== {name} body={body.hex()} =====")
        print(f"  与前缀 XOR: {xor_prefix_pattern(body)}")
        for off in range(0, 5):
            res = try_codecs(body, off)
            for cname, r in res:
                print(f"  [off={off} {cname}] OK {len(r)}B: {r[:120]!r}")
        # 常见魔数比对
        for magic, label in ((b"\x28\xb5\x2f\xfd", "zstd"), (b"\x04\x22\x4d\x18", "lz4"),
                             (b"\x1f\x8b", "gzip"), (b"\x78\x9c", "zlib")):
            if body.startswith(magic):
                print(f"  以 {label} 魔数开头")
    return 0


if __name__ == "__main__":
    sys.exit(main())
