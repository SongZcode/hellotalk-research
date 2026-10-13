"""ht_probe.py — 对抓到的 WS 帧做压缩算法探测 + JWT 解析（一次性侦察工具）"""
import base64
import json
import pathlib
import struct
import zlib

from mitmproxy import io as mio

DUMP = pathlib.Path(r"F:\hellotalk-mitm\artifacts\mitm\flows2.mitm")


def b64d(s: str):
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())


def jwt_decode(tok: str):
    parts = tok.split(".")
    out = {"raw_len": len(tok)}
    if len(parts) >= 2:
        try:
            out["header"] = json.loads(b64d(parts[0]))
        except Exception as e:
            out["header_err"] = str(e)
        try:
            out["payload"] = json.loads(b64d(parts[1]))
        except Exception as e:
            out["payload_err"] = str(e)
    out["sig_len"] = len(parts[2]) if len(parts) > 2 else 0
    return out


def main():
    frames = []
    with open(DUMP, "rb") as fh:
        for flow in mio.FlowReader(fh).stream():
            if not flow.websocket:
                continue
            for m in flow.websocket.messages:
                frames.append((m.from_client, bytes(m.content), m.timestamp))

    print(f"frames: {len(frames)}")

    # 1) 握手明文 JSON
    for i, (fc, raw, ts) in enumerate(frames[:2]):
        z = raw.find(b"\x78\x9c")
        if z >= 0:
            try:
                txt = zlib.decompress(raw[z:])
            except zlib.error:
                txt = zlib.decompressobj().decompress(raw[z:])
            print(f"\n--- frame {i} ({'UP' if fc else 'DN'}) handshake ---")
            obj = json.loads(txt)
            if "jwt" in obj:
                obj["jwt_decoded"] = jwt_decode(obj["jwt"])
                obj["jwt"] = obj["jwt"][:40] + "..."
            print(json.dumps(obj, ensure_ascii=False, indent=2)[:2500])

    # 2) f5 帧尝试 lz4 / zstd / brotli / raw-deflate
    print("\n--- f5 frames ---")
    for i, (fc, raw, ts) in enumerate(frames):
        if raw[0:3] != b"\xf5\x04\x01":
            continue
        body = raw[24:]
        print(f"\nframe {i} len={len(raw)} op={raw[4:8].hex()} bodylen={len(body)}")
        print("  body[:32]", body[:32].hex())
        for name, fn in (
            ("zlib", lambda b: zlib.decompress(b)),
            ("raw-deflate", lambda b: zlib.decompressobj(-15).decompress(b)),
        ):
            try:
                out = fn(body)
                print(f"  [{name}] OK {len(out)}B: {out[:200]!r}")
            except Exception as e:
                print(f"  [{name}] fail {e}")
        try:
            import zstandard as zstd

            for skip in (0, 1, 2, 4, 8):
                try:
                    out = zstd.ZstdDecompressor().decompress(body[skip:])
                    print(f"  [zstd skip={skip}] OK {len(out)}B: {out[:200]!r}")
                    break
                except Exception:
                    pass
        except ImportError:
            pass
        try:
            import lz4.block  # type: ignore

            out = lz4.block.decompress(body, uncompressed_size=1 << 20)
            print(f"  [lz4] OK {len(out)}B: {out[:200]!r}")
        except ImportError:
            print("  [lz4] module not installed")
        except Exception as e:
            print(f"  [lz4] fail {e}")

    # 3) 帧头字段假设校验
    print("\n--- header field check (UP json frames) ---")
    for i, (fc, raw, ts) in enumerate(frames[:24]):
        if len(raw) < 28:
            continue
        a, b = struct.unpack_from("<I", raw, 8), struct.unpack_from("<I", raw, 12)
        rsv, ln = struct.unpack_from("<I", raw, 16), struct.unpack_from("<I", raw, 20)
        print(
            f"  [{i:>2}] {'UP' if fc else 'DN'} magic={raw[0:4].hex()} op={raw[4:8].hex()} "
            f"u8={a} u12={b} rsv={rsv} len={ln} body={raw[24:28].hex()}"
        )


if __name__ == "__main__":
    main()
