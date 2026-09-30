#!/usr/bin/env python3
"""Download archive files listed in manifest.json and check their sha256."""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    downloads = {item["path"]: item["url"] for item in manifest.get("upstream", []) if "path" in item}
    failed = False
    for item in manifest["archive"]:
        path = ROOT / item["path"]
        url = item.get("url") or downloads.get(item["path"])
        expected = item.get("sha256")
        if path.is_file() and expected and sha256(path) == expected:
            print(f"ok {item['path']}")
            continue
        if not url:
            print(f"missing {item['path']} and no url", file=sys.stderr)
            failed = True
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"get {url}")
        urllib.request.urlretrieve(url, path)
        got = sha256(path)
        if expected and got != expected:
            print(f"hash mismatch {item['path']}: {got}", file=sys.stderr)
            failed = True
        else:
            print(f"ok {item['path']} {got}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
