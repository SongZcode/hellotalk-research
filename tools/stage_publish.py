"""stage_publish.py — 生成可公开的发布副本（自动脱敏 + 排除大文件/证据）

用法: python tools\\stage_publish.py [目标目录]
默认目标: F:\\hellotalk-mitm-publish
"""
import pathlib
import re
import shutil
import sys

SRC = pathlib.Path(r"<WORKDIR>")
DST = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(r"<WORKDIR>-publish")

# 脱敏规则：真实标识 → 占位符
SCRUB = [
    (r"<UID>", "<UID>"),
    (r"<DEVICE_ID>", "<DEVICE_ID>"),
    (r"<SESSION_KEY>", "<SESSION_KEY>"),
    (r"<DISTINCT_ID>", "<DISTINCT_ID>"),
    (r"<DEVICE_MODEL>", "<DEVICE_MODEL>"),
    (r"192\.168\.1\.105", "<PHONE_LAN_IP>"),
    (r"192\.168\.1\.108", "<PC_LAN_IP>"),
    # JWT / token 长串
    (r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,}", "<JWT>"),
    (r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", "<GITHUB_TOKEN>"),
    (r"\b[0-9a-f]{32}\b(?=\s*(?:,|\)|$|\"|'))", "<HEX32_REDACTED>"),
]

# 不发布的路径（相对 SRC）
SKIP_DIRS = {"artifacts", "recon", ".git", ".dsh", ".agent-bus", "venv", "node_modules", "__pycache__"}
SKIP_SUFFIX = {".apk", ".so", ".xz", ".mitm", ".db", ".bin", ".png", ".jpg", ".pyc", ".zip", ".log"}
SKIP_NAME_RE = re.compile(r"\.bundle\.js$|^u\d+\.xml$|^g\d+\.xml$|^p\d+\.xml$|^f\d+\.xml$|^m\d+\.xml$")
# 个人安全审计类文档，不进公开仓库
SKIP_DOC_RE = re.compile(r"SECURITY|安全.*(报告|审计)|凭[证据]" )
# 与本机个人环境相关的脚本/文件，不进公开仓库
SKIP_FILES = {
    "AGENTS.md", "_reg.py", "prefs_spy.js", "dbs_spy.js", "db_query.js", "read_sayhi.js",
    "cred_scan.py", "check_repos.py", "final_audit.py", "fix_leaked_keys.py",
    "restore_and_secure.py", "make_env_files.py", "add_stdlib_loader.py",
    "fix_config_loader.py", "patch_filmclaw_config.py", "rebuild_secrets.py",
    "verify_leakfix.py", "verify_all.py", "fx_dbquery.py", "fx_dbs.py", "fx_prefs.py",
    "fx_readsayhi.py", "fx_vipcheck.py", "vipcheck.js",
}
# 个人路径/主机信息，发布前替换
PATH_SCRUB = [
    (r"F:\\hellotalk-mitm", "<WORKDIR>"),
    (r"F:\\hellotalk-vip", "<WORKDIR2>"),
    (r"F:\\Code", "<CODEDIR>"),
    (r"C:\\Users\\17236", "<HOME>"),
]

TEXT_EXT = {".md", ".py", ".js", ".json", ".txt", ".yml", ".yaml", ".sh", ".ps1", ".xml", ".cfg", ".toml"}


def scrub(text: str) -> str:
    for pat, rep in SCRUB:
        text = re.sub(pat, rep, text)
    for pat, rep in PATH_SCRUB:
        text = re.sub(pat, rep, text)
    return text


def main():
    DST.mkdir(parents=True, exist_ok=True)
    # 只清理内容，保留 .git（否则无法继续提交/推送，且 Windows 下 git 对象只读删不掉）
    for item in DST.iterdir():
        if item.name == ".git":
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
        except OSError as e:
            print(f"[warn] 无法清理 {item.name}: {e}")
    copied = skipped = 0
    for p in SRC.rglob("*"):
        rel = p.relative_to(SRC)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.is_dir():
            continue
        if p.suffix.lower() in SKIP_SUFFIX or SKIP_NAME_RE.search(p.name) or SKIP_DOC_RE.search(p.name) or p.name in SKIP_FILES or ".bak-" in p.name:
            skipped += 1
            continue
        # 跳过超大文件
        try:
            if p.stat().st_size > 2_000_000:
                skipped += 1
                continue
        except OSError:
            continue
        out = DST / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix.lower() in TEXT_EXT:
            try:
                raw = p.read_text(encoding="utf-8", errors="replace")
                out.write_text(scrub(raw), encoding="utf-8")
            except Exception:
                shutil.copy2(p, out)
        else:
            shutil.copy2(p, out)
        copied += 1
    print(f"复制 {copied} 个文件，跳过 {skipped} 个（大文件/二进制/证据）")
    total = sum(f.stat().st_size for f in DST.rglob("*") if f.is_file())
    print(f"发布体积: {total/1024/1024:.2f} MB")
    # 复检敏感串
    hits = 0
    for pat, _ in SCRUB[:8]:
        for f in DST.rglob("*"):
            if f.is_file() and f.suffix.lower() in TEXT_EXT:
                if re.search(pat, f.read_text(encoding="utf-8", errors="replace")):
                    print(f"  [警告] 仍含 {pat} -> {f.relative_to(DST)}")
                    hits += 1
    print("脱敏复检:", "通过 ✅" if hits == 0 else f"{hits} 处残留 ❌")
    return 0


if __name__ == "__main__":
    sys.exit(main())
