#!/usr/bin/env python3
"""
hebrew_tsv_to_markdown.py

Convert BSB morphology tables (TSV) into structured Markdown for the
Hebrew/Aramaic Old Testament (WLC text).

Defaults:
  input:  archive/bsb_tables.tsv
  output: prepared/hebrew-ot.md

Usage:
    python3 pipeline/hebrew_tsv_to_markdown.py
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
from collections import defaultdict, OrderedDict
from pathlib import Path

from reading_errata import apply_hebrew_row, load_hebrew_errata

SCRIPT_DIR = Path(__file__).resolve().parent
BEREAN_ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT = BEREAN_ROOT / "archive" / "bsb_tables.tsv"
DEFAULT_OUTPUT = BEREAN_ROOT / "prepared" / "hebrew-ot.md"

# ─────────────────────────────────────────────
# Fixed data
# ─────────────────────────────────────────────
PSALM_119_ACROSTICS = {
    1:   ("&#1488;", "ALEPH"),
    9:   ("&#1489;", "BETH"),
    17:  ("&#1490;", "GIMEL"),
    25:  ("&#1491;", "DALETH"),
    33:  ("&#1492;", "HE"),
    41:  ("&#1493;", "WAW"),
    49:  ("&#1494;", "ZAYIN"),
    57:  ("&#1495;", "HETH"),
    65:  ("&#1496;", "TETH"),
    73:  ("&#1497;", "YODH"),
    81:  ("&#1499;", "KAPH"),
    89:  ("&#1500;", "LAMEDH"),
    97:  ("&#1502;", "MEM"),
    105: ("&#1504;", "NUN"),
    113: ("&#1505;", "SAMEKH"),
    121: ("&#1506;", "AYIN"),
    129: ("&#1508;", "PE"),
    137: ("&#1510;", "TZADE"),
    145: ("&#1511;", "KOPH"),
    153: ("&#1512;", "RESH"),
    161: ("&#1513;", "SIN and SHIN"),
    169: ("&#1514;", "TAW"),
}

PSALM_BOOKS = {
    1:   "Book I (Psalms 1–41)",
    42:  "Book II (Psalms 42–72)",
    73:  "Book III (Psalms 73–89)",
    90:  "Book IV (Psalms 90–106)",
    107: "Book V (Psalms 107–150)",
}


def clean_heading(raw: str) -> str:
    """Extract the section title from Berean multi-class Hdg markup.

    Psalm book openers look like:
      <p class=|suphdg|>BOOK I <p class=|pshdg|>Psalms 1–41 <p class=|hdg|>The Two Paths
    We keep only the real section title (last class=|hdg|>…); BOOK I… comes from
    the dedicated PSALM_BOOKS comment / USFM \\ms1.
    """
    if not raw:
        return ""
    # Prefer explicit section heading class
    hdg_parts = re.findall(r"class=\|hdg\|>([^<]+)", raw, flags=re.I)
    if hdg_parts:
        return hdg_parts[-1].strip()
    # Fallback: last class capture, skipping BOOK N / Psalms range labels
    chunks = re.findall(r"class=\|[^|]*\|>([^<]+)", raw, flags=re.I)
    if chunks:
        for cand in reversed(chunks):
            t = cand.strip()
            if re.match(r"^BOOK\s+[IVXLCDM]+$", t, re.I):
                continue
            if re.match(r"^Psalms?\s+\d", t, re.I):
                continue
            return t
        return chunks[-1].strip()
    m = re.search(r"class=\|[^|]*\|>(.+)$", raw)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return re.sub(r"<[^>]+>", "", raw).strip()


def clean_crossref(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", "", raw)
    text = text.replace("\xa0", " ").strip()
    return re.sub(r"^[\s\u00a0]*", "", text).strip()


def clean_hebrew_word(raw: str) -> str:
    """Normalize WLC cell text from BSB tables for continuous Markdown."""
    if not raw:
        return ""
    text = raw.strip()
    # Zero-width joiner/non-joiner and bidi marks show up in the TSV and
    # split words (e.g. אֱ + ZWJ + ֽלֹהִים). Not part of the Hebrew reading.
    for ch in ("\u200d", "\u200c", "\u200e", "\u200f", "\ufeff"):
        text = text.replace(ch, "")
    # Petuhah/setumah markers sometimes appended after sof pasuq in the TSV.
    # Keep the sof pasuq; drop only the paragraph letter (not real morphology).
    text = re.sub(r"׃[ספ]+$", "׃", text)
    return text.strip()


def parse_verse_ref(ref: str) -> tuple[str | None, int | None, int | None]:
    if not ref or ":" not in ref:
        return None, None, None
    try:
        book_chapter, verse = ref.rsplit(":", 1)
        verse_num = int(verse)
        parts = book_chapter.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], int(parts[1]), verse_num
        return book_chapter, 0, verse_num
    except Exception:
        return None, None, None


def color_span(text: str, color: str) -> str:
    return f'<span style="color:#{color}">{html.escape(text)}</span>'


def normalize_book_name(name: str) -> str:
    """Normalize book names (especially Psalms)."""
    if not name:
        return name
    n = name.strip()
    if n in ("Psalm", "Psalms", "Ps", "Psa"):
        return "Psalm"
    return n


def is_superscription(title: str) -> bool:
    if not title:
        return False
    t = title.lower()
    patterns = [
        r"^a psalm of", r"^a song of", r"^a miktam of", r"^a maskil of",
        r"^a shiggaion of", r"^for the director", r"^to the choirmaster",
        r"^of david", r"^of asaph", r"^of the sons of korah", r"^of solomon",
        r"^of ethan", r"^a prayer of", r"^a song\.?\s*a psalm",
    ]
    for p in patterns:
        if re.search(p, t):
            return True
    if len(title) < 60 and any(w in t for w in [
        "psalm", "song", "maskil", "miktam", "shiggaion", "prayer"
    ]):
        return True
    return False


class OTConverter:
    def __init__(self, input_path: Path):
        self.input_path = input_path
        self.lines: list[str] = []

    def ensure_blank_before_heading(self) -> None:
        """Ensure at least one blank line before a heading."""
        if self.lines and self.lines[-1] != "":
            self.lines.append("")

    def convert(self) -> str:
        books_order: list[str] = []
        # verses[book][chapter][verse] = list of (heb_sort, word, footnote_or_None)
        verses: OrderedDict = OrderedDict()
        headings: dict = {}

        current_ref = None
        current_book = current_chapter = current_verse = None

        print(f"Reading data from {self.input_path}...")

        with self.input_path.open("r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            header = next(reader)

            col_heb_sort = header.index("Heb Sort")
            col_lang = header.index("Language")
            col_heb_text = header.index("WLC / Nestle Base TR RP WH NE NA SBL")
            col_ref = header.index("VerseId")
            # Canonical verse number (WLC); VerseId suffix can lag by one on wayyiqtol
            try:
                col_verse = header.index("Verse")
            except ValueError:
                col_verse = None
            col_hdg = header.index("Hdg")
            col_xref = header.index("Crossref")
            col_fn = header.index("footnotes")

            # WLC body is Hebrew or Aramaic (Ezra 4–7, Daniel 2–7).
            # Greek rows are NT interleave in the same tables file.
            allowed_langs = {"Hebrew", "Aramaic"}
            errata = load_hebrew_errata()

            for row in reader:
                row = apply_hebrew_row(header, row, errata)
                if len(row) <= col_lang or row[col_lang] not in allowed_langs:
                    continue

                verse_ref = row[col_ref].strip() if len(row) > col_ref and row[col_ref] else ""
                verse_col = (
                    row[col_verse].strip()
                    if col_verse is not None and len(row) > col_verse and row[col_verse]
                    else ""
                )
                heb_text = (
                    clean_hebrew_word(row[col_heb_text])
                    if len(row) > col_heb_text and row[col_heb_text]
                    else ""
                )
                hdg_raw = row[col_hdg].strip() if len(row) > col_hdg and row[col_hdg] else ""
                xref_raw = row[col_xref].strip() if len(row) > col_xref and row[col_xref] else ""
                fn_raw = row[col_fn].strip() if len(row) > col_fn and row[col_fn] else ""

                try:
                    heb_sort = float(row[col_heb_sort]) if len(row) > col_heb_sort and row[col_heb_sort] else 999.0
                except ValueError:
                    heb_sort = 999.0

                # Verse column = absolute Bible index; VerseId = book+chapter (+ often sparse :N).
                # Chapter-relative verse = abs - min_abs_in_chapter + 1, tracked per chapter.
                if verse_ref and ":" in verse_ref:
                    book, chapter, verse_from_id = parse_verse_ref(verse_ref)
                    if book:
                        book = normalize_book_name(book)
                        if verse_col.isdigit():
                            abs_v = int(verse_col)
                            # Establish / reuse chapter base absolute index
                            if not hasattr(self, "_chap_base"):
                                self._chap_base = {}  # (book, chapter) -> base abs
                            key_bc = (book, chapter)
                            if key_bc not in self._chap_base:
                                # First absolute seen for this chapter with VerseId becomes
                                # base only if verse_from_id==1; else keep provisional.
                                if verse_from_id == 1:
                                    self._chap_base[key_bc] = abs_v
                                else:
                                    # estimate: abs - (N-1)
                                    self._chap_base[key_bc] = abs_v - (verse_from_id - 1)
                            # Prefer absolute-derived chapter verse when base known
                            base = self._chap_base[key_bc]
                            verse = abs_v - base + 1
                            # If VerseId N is ahead of abs-derived (rare), trust abs
                            # If abs-derived is nonsense (<=0), fall back to VerseId
                            if verse <= 0:
                                verse = verse_from_id
                        else:
                            verse = verse_from_id
                        current_book, current_chapter, current_verse = book, chapter, verse
                        current_ref = (book, chapter, verse)

                        if book not in verses:
                            books_order.append(book)
                            verses[book] = OrderedDict()
                        if chapter not in verses[book]:
                            verses[book][chapter] = OrderedDict()
                        if verse not in verses[book][chapter]:
                            verses[book][chapter][verse] = []
                elif verse_col.isdigit() and current_book is not None:
                    # Sparse VerseId: advance from absolute Verse + chapter base
                    abs_v = int(verse_col)
                    key_bc = (current_book, current_chapter)
                    base = getattr(self, "_chap_base", {}).get(key_bc)
                    if base is not None:
                        verse = abs_v - base + 1
                        if verse > 0 and verse != current_verse:
                            current_verse = verse
                            current_ref = (current_book, current_chapter, current_verse)
                            if current_verse not in verses[current_book][current_chapter]:
                                verses[current_book][current_chapter][current_verse] = []

                if hdg_raw and "hdg" in hdg_raw.lower() and current_ref:
                    # Remove acrostic markup embedded in Hdg (Psalm 119)
                    clean_raw = re.sub(r"<p class=\|acrostic\|>.*", "", hdg_raw, flags=re.I)
                    title = clean_heading(clean_raw)
                    xref = clean_crossref(xref_raw)
                    if title:
                        headings[current_ref] = (title, xref, is_superscription(title))

                if heb_text and current_ref:
                    verses[current_book][current_chapter][current_verse].append(
                        (heb_sort, heb_text, fn_raw if fn_raw else None)
                    )

        print(f"Books found: {len(books_order)}")
        if "Psalm" in verses and 119 in verses["Psalm"]:
            print(f"  Psalm 119: {len(verses['Psalm'][119])} verses")
        print("Generating Markdown...")

        for book in books_order:
            self.lines.append("")
            self.lines.append(f"# {book}")
            self.lines.append("")

            for chapter in verses[book]:
                # Divisions of the 5 Books of Psalms
                if book == "Psalm" and chapter in PSALM_BOOKS:
                    self.lines.append(f"<!-- {PSALM_BOOKS[chapter]} -->")
                    self.lines.append("")

                self.lines.append(f"## {book} {chapter}")
                self.lines.append("")

                chapter_footnotes: list[tuple[str, str]] = []
                fn_letter_counter: dict[int, int] = defaultdict(int)

                for verse in verses[book][chapter]:
                    ref = (book, chapter, verse)
                    raw_words = verses[book][chapter][verse]

                    # Original-language sort order (Heb Sort)
                    sorted_words = sorted(raw_words, key=lambda x: x[0])

                    # Build verse text + footnote markers
                    verse_parts = []
                    for _sort_idx, heb_word, fn_text in sorted_words:
                        if fn_text:
                            cnt = fn_letter_counter[verse]
                            letter = chr(ord("a") + cnt)
                            fn_letter_counter[verse] += 1
                            key = f"{book.replace(' ', '_')}_{chapter}_{verse}_{letter}"
                            chapter_footnotes.append((key, fn_text))
                            verse_parts.append(f"{heb_word}[^{key}]")
                        else:
                            verse_parts.append(heb_word)

                    hebrew_line = " ".join(verse_parts).strip()

                    # ── Psalm 119: acrostic blocks ───────────────────
                    if book == "Psalm" and chapter == 119 and verse in PSALM_119_ACROSTICS:
                        heb_letter, name = PSALM_119_ACROSTICS[verse]
                        # Prefer live Unicode letter over numeric HTML entity
                        letter = html.unescape(heb_letter)

                        # Main psalm title (only on v.1)
                        if verse == 1 and ref in headings:
                            title, xref, _ = headings[ref]
                            self.ensure_blank_before_heading()
                            if xref:
                                self.lines.append(
                                    f"### {title}<br>*{color_span(xref, '0092F2')}*"
                                )
                            else:
                                self.lines.append(f"### {title}")
                            self.lines.append("")

                        # Acrostic block: Hebrew letter + traditional English name
                        self.ensure_blank_before_heading()
                        self.lines.append(f"#### {letter} {name}")
                        self.lines.append("")

                    # ── Section headings / superscription ────────────
                    elif ref in headings:
                        title, xref, is_super = headings[ref]
                        self.ensure_blank_before_heading()
                        if is_super:
                            if xref:
                                self.lines.append(
                                    f"#### {title}<br>*{color_span(xref, '0092F2')}*"
                                )
                            else:
                                self.lines.append(f"#### {title}")
                        else:
                            if xref:
                                self.lines.append(
                                    f"### {title}<br>*{color_span(xref, '0092F2')}*"
                                )
                            else:
                                self.lines.append(f"### {title}")
                        self.lines.append("")

                    # Verse text
                    self.lines.append(f"**{verse}** {hebrew_line}")

                # Chapter footnotes
                if chapter_footnotes:
                    self.lines.append("")
                    for key, note in chapter_footnotes:
                        self.lines.append(f"[^{key}]: {note}")
                self.lines.append("")

        result = "\n".join(self.lines)
        result = re.sub(r"\n{3,}", "\n\n", result)
        return result.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert BSB Tables (TSV) into Hebrew/Aramaic OT Markdown."
    )
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    print(f"Input : {args.input}")
    print(f"Output: {args.output}\n")

    converter = OTConverter(args.input)
    markdown = converter.convert()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    print("\nOK — done")
    print(f"  Characters: {len(markdown):,}")
    print(f"  Lines     : {markdown.count(chr(10)) + 1:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
