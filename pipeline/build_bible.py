#!/usr/bin/env python3
"""Assemble one Markdown file from canon/.

By default book titles are the ordinary English names (`Psalms`).
``--original`` puts the provenance notice first and uses the English names
Berean prints (`Psalm`). ``--testament ot`` keeps folders 01-39.
``--testament nt`` keeps folders 41-67. Chapter files are not changed.
Files in ``extra/`` are left beside the reading text.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from books import books_for, chapter_filename  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "canon"
FRONT = ROOT / "front"
STEM = "bible"
COMMENT_RE = re.compile(r"\A<!--\n.*?\n-->\n+", re.S)
HEADING_RE = re.compile(r"^## .+$", re.M)


def load_titles() -> dict[str, str]:
    text = (FRONT / "titles.md").read_text(encoding="utf-8")
    titles: dict[str, str] = {}
    for part in re.split(r"^## ", text, flags=re.M)[1:]:
        heading, _, body = part.partition("\n")
        titles[heading.strip()] = body.strip().split("\n", 1)[0].strip()
    return titles


def chapter_markdown(book, number: int) -> str:
    path = CANON / book.folder / chapter_filename(book.folder, number)
    text = COMMENT_RE.sub("", path.read_text(encoding="utf-8")).strip()
    return HEADING_RE.sub(f"## {book.chapter_name} {number}", text, count=1)


def build(modern: bool, testament: str | None = None) -> str:
    titles = load_titles()
    parts: list[str] = []
    if not modern:
        notice = (FRONT / "notice.md").read_text(encoding="utf-8").strip()
        notice = re.sub(r"\n<!--\n.*?\n-->\s*\Z", "", notice, count=1, flags=re.S)
        parts.append(notice.strip())
    for book in books_for(testament):
        folder = CANON / book.folder
        numbers = sorted(
            int(path.stem) for path in folder.glob("*.md") if path.stem.isdigit()
        )
        if not numbers:
            continue
        if modern:
            parts.append(f"# {book.modern_name}")
        else:
            parts.append(f"# {titles[book.folder]}")
        for number in numbers:
            parts.append(chapter_markdown(book, number))
    return "\n\n".join(parts).rstrip() + "\n"


def default_output(original: bool, testament: str | None) -> Path:
    pieces = [STEM]
    if original:
        pieces.append("original")
    if testament:
        pieces.append(testament)
    return ROOT / "dist" / ("-".join(pieces) + ".md")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Join canon chapters into one Markdown file."
    )
    parser.add_argument(
        "--original",
        action="store_true",
        help="Provenance notice and the English book titles Berean prints.",
    )
    parser.add_argument(
        "--testament",
        choices=("ot", "nt"),
        help="Only the Old Testament (folders 01-39) or the New Testament (folders 41-67).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Output path. Default: dist/bible.md, with -original and "
            "-ot or -nt added when those options are set."
        ),
    )
    args = parser.parse_args()
    destination = args.output or default_output(args.original, args.testament)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        build(modern=not args.original, testament=args.testament),
        encoding="utf-8",
    )
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
