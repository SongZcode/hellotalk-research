"""Inventory a local APK ZIP without extracting or executing its contents.

Adapted from the project's original apk_probe.py research script.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import zipfile


def inventory(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        dex = sorted((entry for entry in entries if re.fullmatch(r'classes(?:\d+)?\.dex', entry.filename)), key=lambda entry: entry.filename)
        libraries = [entry for entry in entries if re.fullmatch(r'lib/[^/]+/[^/]+\.so', entry.filename)]
        return {
            'entries': len(entries),
            'uncompressed_bytes': sum(entry.file_size for entry in entries),
            'android_manifest': any(entry.filename == 'AndroidManifest.xml' for entry in entries),
            'dex': [{'name': entry.filename, 'bytes': entry.file_size} for entry in dex],
            'native_libraries': len(libraries),
            'abi': dict(sorted(Counter(entry.filename.split('/')[1] for entry in libraries).items())),
            'asset_entries': sum(entry.filename.startswith('assets/') and not entry.is_dir() for entry in entries),
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description='List local base APK structure without extraction')
    parser.add_argument('apk', type=Path)
    args = parser.parse_args(argv)
    if not args.apk.is_file():
        parser.error('APK file does not exist')
    try:
        result = inventory(args.apk)
    except (OSError, zipfile.BadZipFile) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
