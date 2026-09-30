#!/usr/bin/env python3
"""Split the prepared Berean continuous Markdown into one file per chapter.

Reads prepared/hebrew-ot.md and prepared/greek-nt.md. Those files are
written by the extraction scripts from archive/bsb_tables.tsv and
archive/bgb.docx. This script does not edit the Hebrew or Greek words.
It only:

- puts each chapter in canon/NN-BBB/CC.md
- turns a Berean section heading into a Markdown heading, with the
  parallel reference as a subtitle ``#### (John 1:1–5; Hebrews 11:1–3)``
- rewrites footnote ids from the English book slug to the USFM code
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from books import BOOKS, BY_CHAPTER_NAME, BY_SLUG, chapter_filename, note_letter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "canon"
SOURCES = (
    ROOT / "prepared" / "hebrew-ot.md",
    ROOT / "prepared" / "greek-nt.md",
)
EDITION = "berean"
FN_RE = re.compile(r"\[\^((?:[A-Za-z0-9]+_)*)(\d+)_(\d+)_([a-z]+)\]")
DEF_RE = re.compile(
    r"^\[\^((?:[A-Za-z0-9]+_)*)(\d+)_(\d+)_([a-z]+)\]:\s*(.*)$"
)
DEFINITIONS: dict[str, str] = {}


def footnote_id(match: re.Match[str]) -> str:
    book = BY_SLUG.get(match.group(1).rstrip("_"))
    if book is None:
        raise SystemExit(f"unknown footnote book {match.group(1)!r}")
    return f"{book.usfm}_{match.group(2)}_{match.group(3)}_{match.group(4)}"
CHAPTER_RE = re.compile(r"^## (.+) (\d+)\s*$")
HEADING_RE = re.compile(r"^(#{3,4})\s+(.*)$")
TAG_RE = re.compile(r"</?span[^>]*>", re.I)
BR_RE = re.compile(r"<br\s*/?>", re.I)


def rewrite_ids(text: str) -> str:
    return FN_RE.sub(lambda match: f"[^{footnote_id(match)}]", text)


def clean_heading(line: str) -> list[str]:
    match = HEADING_RE.match(line)
    level, raw = match.group(1), match.group(2)
    body = TAG_RE.sub("", raw)
    body = BR_RE.sub("\n", body).replace("*", "")
    parts = [part.strip() for part in body.split("\n") if part.strip()]
    title = parts[0]
    out = [f"{level} {title}", ""]
    if len(parts) > 1:
        parallel = parts[1].strip()
        if parallel.startswith("(") and parallel.endswith(")"):
            parallel = parallel[1:-1].strip()
        out.extend([f"#### ({parallel})", ""])
    return out


def chapters_of(text: str) -> list[tuple[object, int, list[str]]]:
    found: list[tuple[object, int, list[str]]] = []
    book = None
    number = None
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if book is None or number is None:
            buf = []
            return
        while buf and not buf[0].strip():
            buf.pop(0)
        while buf and not buf[-1].strip():
            buf.pop()
        found.append((book, number, buf))
        buf = []

    for raw in text.splitlines():
        if raw.startswith("# "):
            flush()
            book = BY_CHAPTER_NAME[raw[2:].strip()]
            number = None
            continue
        chapter = CHAPTER_RE.match(raw)
        if chapter:
            flush()
            name, num = chapter.group(1), int(chapter.group(2))
            if book is None or name != book.chapter_name:
                raise SystemExit(f"chapter heading {raw!r} outside {book}")
            number = num
            continue
        if number is None:
            defined = DEF_RE.match(raw)
            if defined:
                DEFINITIONS[footnote_id(defined)] = defined.group(5)
            continue
        defined = DEF_RE.match(raw)
        if defined:
            DEFINITIONS[footnote_id(defined)] = defined.group(5)
            continue
        if raw.startswith("### ") or raw.startswith("#### "):
            buf.extend(clean_heading(raw))
        else:
            buf.append(rewrite_ids(raw))
    flush()
    return found


def render(book, number: int, body: list[str]) -> str:
    lines = [
        "<!--",
        f"edition: {EDITION}",
        f"book: {book.folder}",
        f"chapter: {number}",
        f"lang: {book.lang}",
        "-->",
        "",
        f"## {book.chapter_name} {number}",
        "",
        *body,
    ]
    seen: list[str] = []
    for match in re.finditer(r"\[\^([0-9A-Z]+_\d+_\d+_[a-z]+)\]", "\n".join(body)):
        ident = match.group(1)
        if ident not in seen:
            seen.append(ident)
    if seen:
        lines.append("")
        for ident in seen:
            note = DEFINITIONS.get(ident)
            if note is None:
                raise SystemExit(f"missing footnote {ident}")
            lines.append(f"[^{ident}]: {note}")
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return assign_chapter_letters(text.rstrip() + "\n")


NOTE_ID_RE = re.compile(r"^([0-9A-Z]+)_(\d+)_(\d+)_[a-z]+$")
CALL_RE = re.compile(r"\[\^([0-9A-Z]+_\d+_\d+_[a-z]+)\](?!:)")
ANY_ID_RE = re.compile(r"\[\^([0-9A-Z]+_\d+_\d+_[a-z]+)\]")


def assign_chapter_letters(text: str) -> str:
    """Published ids use the chapter's note order, not the source letter.

    The verse stays the verse the call is attached to. A call that sits in
    a heading already carries the first verse of that section.
    """
    seen: list[str] = []
    for match in CALL_RE.finditer(text):
        ident = match.group(1)
        if ident not in seen:
            seen.append(ident)
    mapping: dict[str, str] = {}
    for index, ident in enumerate(seen):
        parsed = NOTE_ID_RE.match(ident)
        if not parsed:
            raise SystemExit(f"bad note id {ident}")
        mapping[ident] = (
            f"{parsed.group(1)}_{parsed.group(2)}_{parsed.group(3)}_"
            f"{note_letter(index)}"
        )

    def repl(match: re.Match[str]) -> str:
        ident = match.group(1)
        return f"[^{mapping.get(ident, ident)}]"

    return ANY_ID_RE.sub(repl, text)


def write_titles() -> None:
    front = ROOT / "front"
    front.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Book titles",
        "",
        "Berean publishes these English names. They are not written into the",
        "chapter files. `pipeline/build_bible.py --original` uses them.",
        "The reading index uses `Psalms` for the book Berean heads as `Psalm`.",
        "",
    ]
    for book in BOOKS:
        lines.extend([f"## {book.folder}", "", book.chapter_name, ""])
    (front / "titles.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_index() -> None:
    lines = [
        "# Canon",
        "",
        "Each number opens a chapter.",
        "",
    ]
    for book in BOOKS:
        folder = CANON / book.folder
        numbers = sorted(
            int(path.stem) for path in folder.glob("*.md") if path.stem.isdigit()
        )
        if not numbers:
            continue
        lines.extend([f"## {book.modern_name}", ""])
        width = min(10, len(numbers))
        cells = [
            f"[{n}](canon/{book.folder}/{chapter_filename(book.folder, n)})"
            for n in numbers[:width]
        ]
        if width == 10:
            cells.extend("" for _ in range(0))
        lines.append("| " + " | ".join(cells) + " |")
        lines.append("|" + "|".join("---" for _ in range(width)) + "|")
        rest = numbers[width:]
        while rest:
            row, rest = rest[:10], rest[10:]
            padded = [
                f"[{n}](canon/{book.folder}/{chapter_filename(book.folder, n)})"
                for n in row
            ]
            padded.extend("" for _ in range(10 - len(padded)))
            lines.append("| " + " | ".join(padded) + " |")
        lines.append("")
    (ROOT / "CANON.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    if CANON.exists():
        for path in CANON.rglob("*.md"):
            path.unlink()
    written = 0
    for source in SOURCES:
        if not source.is_file():
            print(f"missing {source}", file=sys.stderr)
            return 1
        for book, number, body in chapters_of(source.read_text(encoding="utf-8")):
            dest = CANON / book.folder / chapter_filename(book.folder, number)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(render(book, number, body), encoding="utf-8")
            written += 1
    write_titles()
    write_index()
    print(f"chapters {written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
