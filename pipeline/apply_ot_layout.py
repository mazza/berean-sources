#!/usr/bin/env python3
"""Lay the Old Testament out like the New Testament.

``hebrew_tsv_to_markdown.py`` writes a flat verse list. This step runs
after that and does not change a Hebrew or Aramaic word. It only inserts
the paragraph breaks, poetry lines, genealogy lines, and letter blocks
already used in the VFE Old Testament, with the same Markdown as the
Greek New Testament: a leading ``>``, ``&nbsp;`` indents, and ``<br>``.

The decisions are pinned in ``pipeline/ot-layout.json``. Regenerate that
file from a VFE checkout with ``--extract``. A normal rebuild only reads
the pinned file, so the result does not depend on editing ``canon/`` or
``prepared/`` by hand.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
DEFAULT_LAYOUT = SCRIPT_DIR / "ot-layout.json"
DEFAULT_HEBREW = ROOT / "prepared" / "hebrew-ot.md"
DEFAULT_VFE = ROOT.parent / "biblia-vfe" / "canon"

sys.path.insert(0, str(SCRIPT_DIR))
from books import BOOKS, BY_CHAPTER_NAME  # noqa: E402

CHAPTER_RE = re.compile(r"^## (.+) (\d+)\s*$")
VERSE_RE = re.compile(r"\*\*(\d+)\*\*")
HEADING_RE = re.compile(r"^(?:> )?#{3,4} ")
DEF_RE = re.compile(r"^\[\^[^\]]+\]: ")

# Disjunctive accents, strongest first. Conjunctives are not in this list,
# so a split falls at a real pause (atnach, ole, zaqef, …).
ACCENT_RANK = {
    "\u0591": 0,  # atnah
    "\u05a2": 0,  # atnah hafukh
    "\u05ab": 1,  # ole
    "\u0592": 2,  # segolta
    "\u0593": 3,  # shalshelet
    "\u0595": 4,  # zaqef gadol
    "\u0594": 4,  # zaqef qatan
    "\u0597": 5,  # revia
    "\u0596": 6,  # tipeha
    "\u0598": 7,  # zarqa
    "\u0599": 7,  # pashta
    "\u059a": 7,  # yetiv
    "\u059b": 8,  # tevir
    "\u059c": 9,  # geresh
    "\u059d": 9,  # geresh muqdam
    "\u059e": 9,  # gershayim
    "\u05a0": 10,  # telisha gedola
    "\u05a1": 10,  # pazer
    "\u059f": 10,  # qarney para
}


def plain_word_count(line: str) -> int:
    """How many words the VFE line carries. The Hebrew split follows this weight."""
    text = re.sub(r"^(?:>\s*)+", "", line)
    text = text.replace("&nbsp;", " ").replace("<br>", " ")
    text = re.sub(r"\*\*\d+\*\*", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return max(len(text.split()), 1)


def mold_of(line: str, verse: int | None) -> str:
    """Encode one VFE content line. ``q:nbsp:br:num:words``."""
    quote = 1 if line.startswith(">") else 0
    nbsp = line.count("&nbsp;")
    br = 1 if line.rstrip().endswith("<br>") else 0
    num = 1 if verse is not None and f"**{verse}**" in line else 0
    return f"{quote}:{nbsp}:{br}:{num}:{plain_word_count(line)}"


def parse_mold(text: str) -> tuple[int, int, int, int, int]:
    parts = text.split(":")
    quote, nbsp, br, num = (int(parts[index]) for index in range(4))
    words = int(parts[4]) if len(parts) > 4 else 1
    return quote, nbsp, br, num, words


def extract_chapter(text: str) -> dict[str, dict]:
    """VFE chapter → per-verse gap codes and line molds.

    Gap codes, in order, before the verse: ``b`` blank, ``s`` a lone ``>``,
    ``h`` a heading, ``H`` a heading already inside the block.
    Line codes are molds, or ``b`` / ``s`` between the lines of one verse.
    """
    lines = text.splitlines()
    events: list[tuple] = []
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            events.append(("b",))
            continue
        if line == ">":
            events.append(("s",))
            continue
        if line.startswith("<!--") or line.startswith("## "):
            continue
        if HEADING_RE.match(line):
            events.append(("H" if line.startswith(">") else "h",))
            continue
        if line.startswith("#### ") or line.startswith("> #### "):
            events.append(("H" if line.startswith(">") else "h",))
            continue
        found = VERSE_RE.findall(line)
        verse = int(found[0]) if found else None
        events.append(("l", verse, line))

    # Drop the leading and trailing blanks of the chapter.
    while events and events[0][0] == "b":
        events.pop(0)
    while events and events[-1][0] == "b":
        events.pop()

    verses: dict[str, dict] = {}
    gap: list[str] = []
    current: int | None = None
    body: list[str] = []

    def close() -> None:
        nonlocal current, body, gap
        if current is None:
            return
        verses[str(current)] = {"gap": "".join(gap), "lines": body}
        gap = []
        body = []
        current = None

    index = 0
    while index < len(events):
        event = events[index]
        kind = event[0]
        if kind == "l":
            verse = event[1]
            if verse is not None and verse != current:
                close()
                current = verse
            if current is None:
                # A continuation before any verse number. Keep it out.
                index += 1
                continue
            body.append(mold_of(event[2], current))
            index += 1
            continue
        # blank, spacer, or heading. It stays inside the verse only when
        # more text of the same verse follows before the next number.
        if current is not None and kind in {"b", "s"} and continues_verse(events, index, current):
            body.append(kind)
            index += 1
            continue
        close()
        gap.append(kind)
        index += 1
    close()
    if gap:
        verses["end"] = {"gap": "".join(gap), "lines": []}
    return verses


def continues_verse(events: list[tuple], start: int, verse: int) -> bool:
    index = start
    while index < len(events) and events[index][0] in {"b", "s"}:
        index += 1
    if index >= len(events) or events[index][0] != "l":
        return False
    found = events[index][1]
    return found is None or found == verse


def extract_tree(vfe: Path) -> dict:
    layout: dict[str, dict] = {}
    missing: list[str] = []
    for book in BOOKS:
        if book.order > 39:
            continue
        folder = vfe / book.folder
        if not folder.is_dir():
            missing.append(book.folder)
            continue
        files = {int(path.stem): path for path in folder.glob("*.md") if path.stem.isdigit()}
        for number, path in sorted(files.items()):
            layout[f"{book.folder}:{number}"] = extract_chapter(path.read_text(encoding="utf-8"))
    if missing:
        raise SystemExit(f"VFE folders missing: {', '.join(missing)}")
    return layout


def accent_rank(token: str) -> int | None:
    ranks = [ACCENT_RANK[char] for char in token if char in ACCENT_RANK]
    return min(ranks) if ranks else None


def split_by_weights(tokens: list[str], weights: list[int]) -> list[list[str]]:
    """Cut ``tokens`` into ``len(weights)`` pieces, sized like the VFE lines.

    Each cut snaps to a disjunctive accent when one sits next to the
    proportional boundary, so a poetic colon stays on its own line.
    """
    pieces = len(weights)
    if pieces <= 1 or len(tokens) <= 1:
        return [tokens]
    if pieces > len(tokens):
        weights = weights[: len(tokens)]
        pieces = len(weights)
    total = sum(weights) or pieces
    cuts: list[int] = []
    consumed = 0
    for weight in weights[:-1]:
        consumed += weight
        remaining = pieces - len(cuts) - 1
        min_cut = cuts[-1] + 1 if cuts else 0
        max_cut = len(tokens) - 1 - remaining
        if min_cut > max_cut:
            min_cut = max_cut
        ideal = int(round(consumed / total * len(tokens))) - 1
        ideal = min(max(ideal, min_cut), max_cut)
        best = ideal
        best_key = (99, 99)
        for index in range(max(min_cut, ideal - 2), min(max_cut, ideal + 2) + 1):
            rank = accent_rank(tokens[index])
            if rank is None:
                continue
            key = (rank, abs(index - ideal))
            if key < best_key:
                best = index
                best_key = key
        # A maqaf binds this word to the next one. Do not leave "son-of" alone.
        while best < max_cut and tokens[best].endswith("־"):
            best += 1
        cuts.append(best)
    parts: list[list[str]] = []
    start = 0
    for cut in cuts:
        parts.append(tokens[start : cut + 1])
        start = cut + 1
    parts.append(tokens[start:])
    return parts


def render_line(mold: str, text: str, verse: int) -> str:
    quote, nbsp, br, num, _words = parse_mold(mold)
    body = f"**{verse}** {text}".rstrip() if num and text else (f"**{verse}**" if num else text)
    if quote:
        indent = "&nbsp;" * nbsp
        line = f"> {indent}{body}".rstrip()
        if line == ">":
            line = "> "
        # A quoted line with no indent keeps one space after ``>``, matching
        # the Greek New Testament. A line that is only the marker does not.
        if not body and not indent:
            line = ">"
    else:
        line = f"{'&nbsp;' * nbsp}{body}".rstrip()
    if br:
        line += "<br>"
    return line


def quoted_heading(line: str) -> list[str]:
    """Put a prepared heading inside the block without losing its parallel."""
    match = re.match(r"^(#{3,4})\s+(.*)$", line)
    if not match:
        return [f"> {line}"]
    level, raw = match.group(1), match.group(2)
    parallel = ""
    broken = raw.split("<br>", 1)
    title = re.sub(r"<[^>]+>", "", broken[0]).replace("*", "").strip()
    if len(broken) > 1:
        parallel = re.sub(r"<[^>]+>", "", broken[1]).replace("*", "").strip()
        if parallel.startswith("(") and parallel.endswith(")"):
            parallel = parallel[1:-1].strip()
    out = [f"> {level} {title}"]
    if parallel:
        out.extend([">", f"> #### ({parallel})"])
    return out


def content_indexes(codes: list[str], tokens: list[str]) -> list[int]:
    """Which line codes receive Hebrew words.

    A verse with more poetic lines than words keeps the numbered line and
    as many following lines as there are words. Internal blanks stay.
    """
    indexes = [index for index, code in enumerate(codes) if code not in {"b", "s"}]
    if not indexes:
        return []
    limit = max(len(tokens), 1)
    if len(indexes) <= limit:
        return indexes
    # Always keep a line that carries the verse number, then fill in order.
    numbered = [index for index in indexes if parse_mold(codes[index])[3]]
    kept = numbered[:1] or indexes[:1]
    for index in indexes:
        if index in kept:
            continue
        if len(kept) == limit:
            break
        kept.append(index)
    return sorted(kept)


def format_verse(spec: dict, verse: int, hebrew: str) -> list[str]:
    codes = list(spec.get("lines") or [])
    tokens = hebrew.split(" ") if hebrew else []
    indexes = content_indexes(codes, tokens)
    if not indexes:
        return [f"**{verse}** {hebrew}"]
    if not any(parse_mold(codes[index])[3] for index in indexes):
        quote, nbsp, br, _num, words = parse_mold(codes[indexes[0]])
        codes[indexes[0]] = f"{quote}:{nbsp}:{br}:1:{words}"
    weights = [parse_mold(codes[index])[4] for index in indexes]
    parts = split_by_weights(tokens, weights)
    out: list[str] = []
    cursor = 0
    index_set = set(indexes)
    for index, code in enumerate(codes):
        if code == "b":
            # A blank inside the verse is the address/body break. Keep it
            # only when a content line on each side survived.
            if cursor and cursor < len(indexes):
                out.append("")
            continue
        if code == "s":
            if cursor and cursor < len(indexes):
                out.append(">")
            continue
        if index not in index_set:
            continue
        text = " ".join(parts[cursor]).strip()
        # "son-of" is written with a maqaf and belongs on the next name's line.
        if (
            text.endswith("־")
            and not parse_mold(code)[3]
            and cursor + 1 < len(parts)
        ):
            parts[cursor + 1] = parts[cursor] + parts[cursor + 1]
            cursor += 1
            continue
        cursor += 1
        if not text and not parse_mold(code)[3]:
            continue
        out.append(render_line(code, text, verse))
    return out


def load_layout(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def chapter_key(book_name: str, number: int) -> str:
    book = BY_CHAPTER_NAME[book_name]
    return f"{book.folder}:{number}"


def apply_layout_text(markdown: str, layout: dict) -> tuple[str, dict]:
    """Return formatted Markdown and a small report. Words are checked."""
    if "\n> " in markdown or markdown.startswith("> "):
        raise SystemExit(
            "prepared/hebrew-ot.md is already laid out. "
            "Run hebrew_tsv_to_markdown.py, which writes the flat text first."
        )
    lines = markdown.splitlines()
    out: list[str] = []
    stats = {
        "chapters": 0,
        "verses": 0,
        "split": 0,
        "missing_layout": 0,
        "word_errors": 0,
    }
    index = 0
    while index < len(lines):
        chapter = CHAPTER_RE.match(lines[index])
        if not chapter or chapter.group(1) not in BY_CHAPTER_NAME:
            out.append(lines[index])
            index += 1
            continue
        name, number = chapter.group(1), int(chapter.group(2))
        if BY_CHAPTER_NAME[name].order > 39:
            out.append(lines[index])
            index += 1
            continue
        out.append(lines[index])
        index += 1
        body: list[str] = []
        while index < len(lines) and not lines[index].startswith("## ") and not lines[index].startswith("# "):
            body.append(lines[index])
            index += 1
        formatted, report = format_chapter(body, layout.get(chapter_key(name, number), {}))
        stats["chapters"] += 1
        stats["verses"] += report["verses"]
        stats["split"] += report["split"]
        stats["missing_layout"] += report["missing"]
        stats["word_errors"] += report["errors"]
        # A chapter opens with a blank line after the heading, as the flat
        # file does. format_chapter does not repeat that leading blank.
        if out and out[-1] != "":
            out.append("")
        out.extend(formatted)
        if index < len(lines) and out and out[-1] != "":
            out.append("")
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"
    return text, stats


def format_chapter(body: list[str], spec: dict) -> tuple[list[str], dict]:
    report = {"verses": 0, "split": 0, "missing": 0, "errors": 0}
    items: list[tuple] = []
    footnotes: list[str] = []
    pending: list[str] = []
    for line in body:
        if not line.strip():
            continue
        if DEF_RE.match(line):
            footnotes.append(line)
            continue
        if line.startswith("###") or line.startswith("####") or line.startswith("<!--"):
            pending.append(line)
            continue
        match = VERSE_RE.match(line)
        if match:
            hebrew = line[match.end() :].strip()
            items.append((int(match.group(1)), pending, hebrew))
            pending = []
            continue
        # Anything else stays in front of the next verse.
        pending.append(line)
    out: list[str] = []
    open_quote = False

    def emit(line: str) -> None:
        nonlocal open_quote
        out.append(line)
        if line == "":
            open_quote = False
        elif line.startswith(">"):
            open_quote = True
        elif not line.startswith(">"):
            open_quote = False

    for verse, headings, hebrew in items:
        report["verses"] += 1
        verse_spec = spec.get(str(verse))
        if verse_spec is None:
            report["missing"] += 1
            for heading in headings:
                if out and out[-1] != "":
                    emit("")
                emit(heading)
                emit("")
            emit(f"**{verse}** {hebrew}")
            continue
        content_codes = [code for code in verse_spec["lines"] if code not in {"b", "s"}]
        if len(content_codes) > 1:
            report["split"] += 1
        rendered = format_verse(verse_spec, verse, hebrew)
        rebuilt = verse_words(rendered, verse)
        if rebuilt != hebrew:
            report["errors"] += 1
            # Keep the words exact if a split ever drifts.
            rendered = [f"**{verse}** {hebrew}"]
            content_codes = ["0:0:0:1"]
        gap = verse_spec.get("gap", "")
        heading_iter = iter(headings)
        consumed = False
        for code in gap:
            if code in {"h", "H"}:
                heading = next(heading_iter, None)
                if heading is None:
                    continue
                consumed = True
                if code == "H" or (open_quote and code == "h"):
                    if out and out[-1] not in {"", ">"} and not open_quote:
                        emit("")
                    for piece in quoted_heading(heading):
                        emit(piece)
                else:
                    if out and out[-1] != "":
                        emit("")
                    emit(heading)
                    emit("")
                continue
            if code == "b":
                if out and out[-1] != "":
                    emit("")
                continue
            if code == "s":
                emit(">")
        for heading in heading_iter:
            # A Berean heading the VFE gap did not name. Keep it, inside
            # the letter when the block is already open.
            if open_quote:
                if out and out[-1] not in {">", ""}:
                    emit(">")
                for piece in quoted_heading(heading):
                    emit(piece)
                emit(">")
            else:
                if out and out[-1] != "":
                    emit("")
                emit(heading)
                emit("")
            consumed = True
        if not headings:
            consumed = True
        for line in rendered:
            emit(line)
        if not consumed:
            pass
    if pending:
        if out and out[-1] != "":
            out.append("")
        out.extend(pending)
    end = spec.get("end", {})
    for code in end.get("gap", ""):
        if code == "b" and out and out[-1] != "":
            out.append("")
        elif code == "s":
            out.append(">")
    if footnotes:
        if out and out[-1] != "":
            out.append("")
        out.extend(footnotes)
    # Drop a trailing run of blank lines; the chapter joiner adds one.
    while out and out[-1] == "":
        out.pop()
    return out, report


def verse_words(rendered: list[str], verse: int) -> str:
    """Hebrew words of one rendered verse, in order, for the exact-text check."""
    pieces: list[str] = []
    for line in rendered:
        if line in {"", ">"}:
            continue
        text = re.sub(r"^(?:> )?", "", line)
        text = text.replace("&nbsp;", "").replace("<br>", "")
        text = re.sub(rf"^\*\*{verse}\*\*\s*", "", text)
        text = text.strip()
        if text:
            pieces.append(text)
    return " ".join(pieces)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extract",
        type=Path,
        metavar="VFE_CANON",
        help="Read a VFE canon/ tree and rewrite pipeline/ot-layout.json.",
    )
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT)
    parser.add_argument("--input", type=Path, default=DEFAULT_HEBREW)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Apply in memory and print the report. Do not write.",
    )
    args = parser.parse_args()
    if args.extract:
        layout = extract_tree(args.extract)
        args.layout.write_text(
            json.dumps(layout, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {args.layout} chapters {len(layout)}")
        return 0
    if not args.layout.is_file():
        raise SystemExit(f"missing layout {args.layout}; run --extract first")
    layout = load_layout(args.layout)
    source = args.input.read_text(encoding="utf-8")
    formatted, stats = apply_layout_text(source, layout)
    print(
        "chapters {chapters} verses {verses} split {split} "
        "missing {missing_layout} word_errors {word_errors}".format(**stats)
    )
    if stats["word_errors"]:
        return 1
    if args.check:
        return 0
    destination = args.output or args.input
    destination.write_text(formatted, encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
