"""find_req_model.py — 找到某接口的 Retrofit 接口定义 → 参数模型类 → 字段名

用法: python tools\\find_req_model.py vip_privilege/receive
"""
import pathlib
import re
import sys

ROOTS = [p for p in pathlib.Path(r"F:\hellotalk-vip\artifacts").glob("apktool*/smali*") if p.is_dir()]
PEW = re.compile(r'value = "([^"]+)"')


def scan_for(needle: str):
    for root in ROOTS:
        for f in root.rglob("*.smali"):
            try:
                t = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if needle in t:
                yield f, t


def methods_with(t: str, needle: str):
    parts = list(re.finditer(r"\.method[^\n]*\n", t))
    for i, m in enumerate(parts):
        s = m.start()
        e = parts[i + 1].start() if i + 1 < len(parts) else len(t)
        body = t[s:e]
        if needle in body:
            yield m.group(0).strip(), body


def main():
    needle = sys.argv[1] if len(sys.argv) > 1 else "vip_privilege/receive"
    for f, t in scan_for(needle):
        print(f"\n===== 接口类: {f.name}  ({f.parent.name}) =====")
        for sig, body in methods_with(t, needle):
            print(f"  {sig}")
            params = re.findall(r"\.param p\d+\s+#\s+(L[A-Za-z0-9_/$]+;)", body)
            print(f"     参数类型: {params}")
        # 尝试打印该接口类的模型类字段
        types = set()
        for sig, body in methods_with(t, needle):
            types.update(re.findall(r"\.param p\d+\s+#\s+(L[A-Za-z0-9_/$]+;)", body))
        for ty in types:
            cls = ty.strip("L;").split("/")[-1]
            for root in ROOTS:
                cands = list(root.rglob(f"{cls}.smali"))
                if not cands:
                    continue
                ct = cands[0].read_text(encoding="utf-8", errors="replace")
                print(f"\n  --- 请求模型 {cls} 的字段 ---")
                fields = re.findall(r'\.field[^\n]*\n(?:\s*\.annotation[^\n]*\n(?:\s*value = "([^"]+)"\n)?\s*\.end annotation\n)?', ct)
                # 用更直接的办法：抓所有 value = "xxx"
                names = []
                for m in re.finditer(r'\.field [^\n]*\n\s*\.annotation[^\n]*\n\s*value = "([^"]+)"', ct):
                    names.append(m.group(1))
                print("     ", sorted(set(names)) or "(未找到注解字段)")
                break
    return 0


if __name__ == "__main__":
    sys.exit(main())
