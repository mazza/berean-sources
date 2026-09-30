#!/usr/bin/env python3
"""
greek_docx_to_markdown.py

Convert the prepared BGB DOCX into structured Markdown for the
New Testament Greek text.

Defaults:
  input:  prepared/_work/bgb-edited.docx
  output: prepared/greek-nt.md

Usage:
    python3 pipeline/greek_docx_to_markdown.py
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import docx
from docx import Document
from docx.oxml.ns import qn

SCRIPT_DIR = Path(__file__).resolve().parent
BEREAN_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
from books import note_letter  # noqa: E402

DEFAULT_INPUT = BEREAN_ROOT / "prepared" / "_work" / "bgb-edited.docx"
DEFAULT_OUTPUT = BEREAN_ROOT / "prepared" / "greek-nt.md"

PROVENANCE_COMMENT = """\
<!--
  Generated from the Berean Greek Bible (BGB) New Testament DOCX
  published by Bible Hub / Berean Bible (https://berean.bible/), CC0.

  Prepared continuous Markdown from archive/bgb.docx.
  A star (*) flags a spelling updated from Nestle where NA and SBL agree.
  The letters stay and the star is dropped. Word-order arrows (⇔) and
  compound marks (¦, ‿) become footnotes. See docs/notation.md.
-->
"""

# Berean inline apparatus. See docs/notation.md.
ARROW = "\u21d4"  # ⇔
BAR = "\u00a6"  # ¦
TIE = "\u203f"  # ‿
COMPOUND_MARKS = {BAR, TIE}
ORDER_NOTE = "The Berean Greek Bible marks a word-order variant here: {quote}."
COMPOUND_NOTE = "The Berean Greek Bible marks a compound-word variant here: {quote}."
# Joining on ¦ or spacing on ‿ is the reading, except these five.
# The footnote still quotes the mark. The apostrophe is U+2019.
COMPOUND_READINGS = (
    ("ἀγαθὸνποιῆσαι", "ἀγαθὸν ποιῆσαι"),
    ("κάτωκύψας", "κάτω κύψας"),
    ("ἌραΓε", "Ἄραγε"),
    ("ΜήΠοτε", "Μήποτε"),
    ("καθ εἷς", "καθ\u2019 εἷς"),
)

# Verse number at the start of the line (may be inside a <span...>)
START_VERSE_RE = re.compile(
    r"^(<span[^>]*>)?(\d{1,3})([\s\u00a0]+)"
)

# Verse number in the middle of the text
MID_VERSE_RE = re.compile(
    r"(?<!\*)(?<!\*\*)"                 # not already bold
    r"([\.\;\:\?\!\,’\”»\)\s]|</span>)" # separator before (including </span>)
    r"(<span[^>]*>)?"                   # optional <span...> tag
    r"(\d{1,3})"                        # verse number
    r"([\s\u00a0]+)"                    # space
    r"(?:<span[^>]*>)?"                 # optional post-space tag
    r"(?=[Α-Ωα-ωἀ-ὡἈ-Ὡ‹“‘\"\(\[])"       # lookahead: Greek, quotes, ‹, (, [
)


def get_left_indent_pt(para) -> float | None:
    try:
        if para.paragraph_format.left_indent is not None:
            return round(para.paragraph_format.left_indent.pt, 1)
    except Exception:
        pass
    return None


def get_paragraph_indentation(para) -> tuple[bool, str]:
    style_name = (para.style.name if para.style else "").lower()
    indent_pt = get_left_indent_pt(para)

    if style_name in ("indent2", "indentred2"):
        return True, "&nbsp;" * 8
    # indent1stline* is w:left="450", the same left indent as indent1.
    # The style name is not a first-line-only indent.
    if style_name in (
        "indent1",
        "indentred1",
        "indent1stline",
        "indent1stlinered",
    ):
        return True, "&nbsp;" * 4

    if indent_pt is not None:
        if indent_pt >= 35:
            return True, "&nbsp;" * 8
        if indent_pt >= 12:
            return True, "&nbsp;" * 4

    return False, ""


def is_run_red(run, para) -> bool:
    try:
        if run.font and run.font.color and run.font.color.rgb:
            c = str(run.font.color.rgb).upper()
            if c in {
                "FF0000", "RED", "C00000", "990000",
                "E00000", "CC0000", "D80000", "FF3333",
            }:
                return True
    except Exception:
        pass

    rPr = run._element.rPr
    if rPr is not None:
        color = rPr.find(qn("w:color"))
        if color is not None:
            val = color.attrib.get(qn("w:val"))
            if val and val.upper() in {
                "FF0000", "RED", "C00000", "990000",
                "E00000", "CC0000", "D80000", "FF3333",
            }:
                return True
        rstyle = rPr.find(qn("w:rStyle"))
        if rstyle is not None:
            val = rstyle.attrib.get(qn("w:val"))
            if val and "red" in val.lower():
                return True

    if para.style and "red" in (para.style.name or "").lower():
        return True

    return False


def is_run_blue(run) -> bool:
    rPr = run._element.rPr
    if rPr is not None:
        rstyle = rPr.find(qn("w:rStyle"))
        if rstyle is not None:
            val = rstyle.attrib.get(qn("w:val"))
            if val and "cross" in val.lower():
                return True
        color = rPr.find(qn("w:color"))
        if color is not None:
            val = color.attrib.get(qn("w:val"))
            if val and val.upper() in {
                "0092F2", "BLUE", "0000FF", "1B75BC",
                "0070C0", "00A2E8", "0066CC",
            }:
                return True
    return False


def parse_footnote_block(text: str) -> list[tuple[str, str, str]]:
    notes = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        m = re.match(r"^([a-z])\s+(\d+)(?:-\d+)?\s+(.+)$", line, re.IGNORECASE | re.DOTALL)
        if m:
            notes.append((m.group(1).lower(), m.group(2), m.group(3).strip()))
        else:
            m2 = re.match(r"^([a-z])\s+(.+)$", line, re.IGNORECASE | re.DOTALL)
            if m2:
                notes.append((m2.group(1).lower(), "", m2.group(2).strip()))
    return notes


RED_OPEN = '<span style="color:#FF0000">'
RED_CLOSE = "</span>"
EMPTY_RED_RE = re.compile(
    r'<span style="color:#FF0000">\s*</span>'
)


def _hoist_start(match: re.Match[str]) -> str:
    """A verse number that opens a line stays outside any red span."""
    span = match.group(1) or ""
    number = f"**{match.group(2)}**"
    space = match.group(3)
    if span:
        return f"{number}{space}{span}"
    return f"{number}{space}"


def _hoist_mid(match: re.Match[str]) -> str:
    """Split at a verse number and leave **N** outside the following span."""
    sep = match.group(1)
    span = match.group(2) or ""
    number = f"**{match.group(3)}**"
    space = match.group(4)
    return f"{sep}\n{number}{space}{span}"


def drop_empty_red(line: str) -> str:
    line = re.sub(
        rf'({re.escape(RED_OPEN)})\s*(\*\*\d+\*\*)\s*',
        r"\2 \1",
        line,
    )
    return EMPTY_RED_RE.sub("", line)


# A verse marker left inside a red span. The split regex misses a number
# when the separator is Greek ano teleia (U+0387) or the next letter is
# outside its lookahead; a later pass then bolds that number in place.
_RED_VERSE_RE = re.compile(
    r'(<span style="color:#FF0000">)'
    r'([^<]*?)'
    r'(\*\*\d+\*\*)'
    r'([ \t]*)'
)


def hoist_markers_out_of_red(text: str) -> str:
    """Keep **N** outside red spans, and close a span at the verse boundary."""

    def repl(match: re.Match[str]) -> str:
        open_tag = match.group(1)
        before = match.group(2).rstrip()
        marker = match.group(3)
        if not before:
            return f"{marker} {open_tag}"
        return f"{open_tag}{before}{RED_CLOSE}\n{marker} {open_tag}"

    lines: list[str] = []
    for line in text.split("\n"):
        if line.startswith("[^"):
            lines.append(line)
            continue
        previous = None
        while previous != line:
            previous = line
            line = _RED_VERSE_RE.sub(repl, line)
        lines.append(line)
    text = "\n".join(lines)
    text = EMPTY_RED_RE.sub("", text)
    text = re.sub(r"(\*\*\d+\*\*)[ \t]+(?=\n|$)", r"\1", text)
    return text


def bold_and_split_verse_numbers(content: str) -> list[str]:
    # Clean adjacent span fragmentations caused by footnotes
    content = re.sub(r'</span>\s*<span style="color:#FF0000">', '', content)

    # Bold at the start of the string. The number stays outside the span.
    content = START_VERSE_RE.sub(_hoist_start, content)

    # Bold and insert a line break in the middle. **N** starts the new line.
    content = MID_VERSE_RE.sub(_hoist_mid, content)

    parts = [drop_empty_red(p.strip()) for p in content.split("\n")]
    parts = [p for p in parts if p.strip()]
    return fix_html_spans_across_lines(parts) if parts else [content.strip()]


def fix_html_spans_across_lines(lines: list[str]) -> list[str]:
    """
    Ensure each standalone line has perfectly matched open and close
    <span> / </span> tags when red text spans multiple verses.
    """
    fixed_lines = []
    in_red = False
    red_open_tag = '<span style="color:#FF0000">'
    close_tag = '</span>'

    for line in lines:
        if not line:
            fixed_lines.append(line)
            continue

        if in_red:
            marker = re.match(r"(\*\*\d+\*\*)([\s\u00a0]*)", line)
            if marker:
                current_line = (
                    f"{marker.group(1)}{marker.group(2)}{red_open_tag}"
                    f"{line[marker.end():]}"
                )
            else:
                current_line = red_open_tag + line
        else:
            current_line = line

        # Remove redundancies within the same line
        current_line = re.sub(r'</span>\s*<span style="color:#FF0000">', '', current_line)

        opens = len(re.findall(r'<span style="color:#FF0000">', current_line))
        closes = len(re.findall(r'</span>', current_line))

        diff = opens - closes
        if diff > 0:
            current_line += close_tag * diff
            in_red = True
        elif diff < 0:
            for _ in range(abs(diff)):
                current_line = red_open_tag + current_line
            in_red = False
        else:
            in_red = False

        fixed_lines.append(drop_empty_red(current_line))

    return fixed_lines


class VerseLine:
    def __init__(self, text: str, verse_num: str = "", is_heading: bool = False):
        self.text = text
        self.verse_num = verse_num
        self.is_heading = is_heading




def nfc_outside_tags(text: str) -> str:
    """NFC the reading text. Tags and the poetry mold are ASCII and stay put."""
    parts = re.split(r"(<[^>\n]+>)", text)
    return "".join(
        part if part.startswith("<") else unicodedata.normalize("NFC", part)
        for part in parts
    )


def _replace_reading_lines(text: str, rules: list[tuple[str, str, str]]) -> str:
    """Replace in the reading. Footnote definitions keep the source spelling."""
    lines = text.split("\n")
    body = "\n".join(line for line in lines if not line.startswith("[^"))
    for rule_id, frm, _to in rules:
        if frm not in body:
            raise SystemExit(f"{rule_id} matched nothing in the reading")
    out: list[str] = []
    for line in lines:
        if not line.startswith("[^"):
            for _rule_id, frm, to in rules:
                line = line.replace(frm, to)
        out.append(line)
    return "\n".join(out)


def apply_compound_readings(text: str) -> str:
    """Five compound marks whose reading is not the mechanical join or space."""
    rules = [
        (f"compound {src}", src, dst) for src, dst in COMPOUND_READINGS
    ]
    return _replace_reading_lines(text, rules)


def apply_berean_errata(text: str, errata_path: Path | None = None) -> str:
    """Wrong letters, accents, and breathings in pipeline/errata.tsv."""
    path = errata_path or (SCRIPT_DIR / "errata.tsv")
    if not path.is_file():
        raise SystemExit(f"missing {path}")
    rules: list[tuple[str, str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            frm = (row.get("from") or "").strip()
            to = (row.get("to") or "").strip()
            if frm:
                rules.append((row.get("id") or frm, frm, to))
    if not rules:
        raise SystemExit(f"no rules in {path}")
    return _replace_reading_lines(text, rules)


def _is_greek_word_char(ch: str) -> bool:
    """Greek letters, combining marks, apostrophe, and koronis."""
    if ch in {"\u2019", "\u1fbd"}:
        return True
    if ord(ch) < 0x0370:
        return False
    category = unicodedata.category(ch)
    return category.startswith("L") or category == "Mn"


def _prev_greek_word(text: str) -> str:
    i = len(text) - 1
    while i >= 0 and not _is_greek_word_char(text[i]):
        i -= 1
    end = i + 1
    while i >= 0 and _is_greek_word_char(text[i]):
        i -= 1
    return text[i + 1 : end]


def _next_greek_word(text: str) -> str:
    i = 0
    limit = min(len(text), 80)
    while i < limit and not _is_greek_word_char(text[i]):
        if text[i] == "«":
            return ""
        i += 1
    start = i
    while i < len(text) and _is_greek_word_char(text[i]):
        i += 1
    return text[start:i]


def _closing_guillemet(text: str) -> str:
    """Span ending at », allowing a comma or period before the arrow."""
    body = text.rstrip()
    while body and body[-1] in ",.;··":
        body = body[:-1].rstrip()
    if not body.endswith("»"):
        return ""
    open_at = body.rfind("«")
    if open_at < 0:
        return ""
    return body[open_at:]


def _opening_guillemet(text: str) -> str:
    body = text.lstrip()
    if not body.startswith("«"):
        return ""
    close_at = body.find("»")
    if close_at < 0:
        return ""
    return body[: close_at + 1]


def _first_greek_word(text: str) -> str:
    i = 0
    while i < len(text) and not _is_greek_word_char(text[i]):
        i += 1
    start = i
    while i < len(text) and _is_greek_word_char(text[i]):
        i += 1
    return text[start:i]


def _run_text(para) -> str:
    """Run text only. Footnote-call letters live on hyperlinks and stay out."""
    parts: list[str] = []
    for child in para._element:
        if child.tag.split("}")[-1] != "r":
            continue
        parts.append("".join(t.text or "" for t in child.findall(".//" + qn("w:t"))))
    return "".join(parts)


def _normalize_quote(text: str) -> str:
    return " ".join(text.replace("\u00a0", " ").replace("*", "").split())


@dataclass(frozen=True)
class NotationMark:
    kind: str
    insert_at: int
    quote: str


def find_notation(raw: str, following_word: str = "") -> list[NotationMark]:
    """Word-order and compound marks in run text.

    A compound chain (μὲν‿ οὖν‿ γε) is one note. The call sits at
    ``insert_at`` in ``raw``: on the arrow, or just after the compound.
    """
    marks: list[NotationMark] = []
    n = len(raw)
    i = 0
    while i < n:
        if raw[i] not in COMPOUND_MARKS:
            i += 1
            continue
        j = i - 1
        while j >= 0 and raw[j] in " \u00a0":
            j -= 1
        while j >= 0 and _is_greek_word_char(raw[j]):
            j -= 1
        start = j + 1
        k = i
        while k < n and raw[k] in COMPOUND_MARKS:
            k += 1
            while k < n and raw[k] in " \u00a0":
                k += 1
            if k < n and _is_greek_word_char(raw[k]):
                while k < n and _is_greek_word_char(raw[k]):
                    k += 1
                continue
            break
        piece = raw[start:k]
        extra = ""
        if piece and piece[-1] in COMPOUND_MARKS and following_word:
            extra = " " + following_word
        quote = _normalize_quote(piece + extra)
        if BAR not in quote and TIE not in quote:
            raise SystemExit(f"compound mark has no quote in {raw[start:k]!r}")
        marks.append(NotationMark("compound", k, quote))
        i = max(k, i + 1)

    for index, ch in enumerate(raw):
        if ch != ARROW:
            continue
        left, right = raw[:index], raw[index + 1 :]
        left_span = _closing_guillemet(left)
        right_span = _opening_guillemet(right)
        if left_span and right_span:
            quote = f"{left_span} {ARROW} {right_span}"
        elif left_span:
            quote = f"{left_span} {ARROW} {_next_greek_word(right)}"
        elif right_span:
            quote = f"{_prev_greek_word(left)} {ARROW} {right_span}"
        else:
            quote = f"{_prev_greek_word(left)} {ARROW} {_next_greek_word(right)}"
        quote = _normalize_quote(quote)
        side_l, _, side_r = quote.partition(f" {ARROW} ")
        if not side_l or not side_r:
            raise SystemExit(f"word-order mark has no quote in {raw[max(0, index - 20):index + 20]!r}")
        marks.append(NotationMark("order", index, quote))

    covered = sum(mark.quote.count(BAR) + mark.quote.count(TIE) for mark in marks if mark.kind == "compound")
    if covered != raw.count(BAR) + raw.count(TIE):
        raise SystemExit("a compound mark was left out of its footnote")
    if sum(mark.kind == "order" for mark in marks) != raw.count(ARROW):
        raise SystemExit("a word-order arrow was left out of its footnote")
    return marks


def _following_greek_word(paragraphs, index: int) -> str:
    """First Greek word after a compound mark that ends a paragraph."""
    for para in paragraphs[index + 1 : index + 5]:
        style = para.style.name if para.style else ""
        if style in {"Heading 1", "Heading 2", "foot"}:
            return ""
        word = _first_greek_word(_run_text(para))
        if word:
            return word
        if style in {"Heading 3", "hdg"}:
            return ""
    return ""


class BGBConverter:
    def __init__(self, docx_path: Path):
        self.doc = Document(str(docx_path))
        self.lines: list[str] = []
        self.current_book = ""
        self.current_chapter = ""
        self.current_verse = ""

        self.chapter_verses: list[VerseLine] = []
        self.chapter_footnotes: list[tuple[str, str, str]] = []
        self.text_calls_map: dict[str, str] = {}
        self.last_was_indented = False
        self.started = False
        self.notation_index = 0
        self.notation_counts = {"order": 0, "compound": 0}

    def flush_chapter(self) -> None:
        if not self.chapter_verses and not self.chapter_footnotes:
            return

        def_lines = []
        for letter, v_num_fn, content in self.chapter_footnotes:
            target_v = self.text_calls_map.get(
                letter, v_num_fn or self.current_verse or "0"
            )
            key = f"{self.current_book}_{self.current_chapter}_{target_v}_{letter}"
            def_lines.append(f"[^{key}]: {content}")

        for obj in self.chapter_verses:
            self.lines.append(obj.text)

        if def_lines:
            if self.lines and self.lines[-1] != "":
                self.lines.append("")
            for d in def_lines:
                self.lines.append(d)
            self.lines.append("")

        self.chapter_verses.clear()
        self.chapter_footnotes.clear()
        self.text_calls_map.clear()
        self.last_was_indented = False
        self.notation_index = 0

    def _notation_call(self, verse: str, mark: NotationMark) -> str:
        if not self.current_book or not self.current_chapter or not verse:
            raise SystemExit(f"notation mark outside a verse: {mark.quote}")
        suffix = "n" + note_letter(self.notation_index)
        self.notation_index += 1
        self.notation_counts[mark.kind] += 1
        template = ORDER_NOTE if mark.kind == "order" else COMPOUND_NOTE
        self.chapter_footnotes.append((suffix, verse, template.format(quote=mark.quote)))
        return (
            f"[^{self.current_book}_{self.current_chapter}_{verse}_{suffix}]"
        )

    def _render_paragraph(self, para, para_index: int, paragraphs) -> str:
        """Reading text for one paragraph, with a footnote at each apparatus mark.

        Stars are dropped. A broken bar joins the parts, and an undertie
        becomes a space. An arrow is deleted and the written order stays.
        The footnote quotes the mark. See docs/notation.md.
        """
        events: list[tuple] = []
        verse = self.current_verse
        raw_parts: list[str] = []
        verses: list[str] = []
        for child in para._element:
            tag = child.tag.split("}")[-1]
            if tag == "r":
                run = docx.text.run.Run(child, para)
                r_text = run.text
                if not r_text:
                    continue
                rPr = child.find(qn("w:rPr"))
                if rPr is not None:
                    rstyle_ele = rPr.find(qn("w:rStyle"))
                    if (
                        rstyle_ele is not None
                        and rstyle_ele.attrib.get(qn("w:val")) == "reftext1"
                    ):
                        m_v = re.search(r"(\d+)", r_text)
                        if m_v:
                            verse = m_v.group(1)
                            self.current_verse = verse
                events.append(("run", r_text, is_run_red(run, para), verse))
                raw_parts.append(r_text)
                verses.extend([verse] * len(r_text))
            elif tag == "hyperlink":
                hl_text = "".join(
                    t.text for t in child.findall(".//" + qn("w:t")) if t.text
                ).strip().lower()
                events.append(("fn", hl_text, verse))

        raw = "".join(raw_parts)
        following = ""
        stripped = raw.rstrip()
        if stripped and stripped[-1] in COMPOUND_MARKS:
            following = _following_greek_word(paragraphs, para_index)
        marks = (
            find_notation(raw, following)
            if any(ch in raw for ch in (ARROW, BAR, TIE))
            else []
        )
        pending: dict[int, list[tuple[str, NotationMark]]] = {}
        for mark in marks:
            if mark.kind == "order":
                verse_at = verses[mark.insert_at]
            else:
                verse_at = verses[mark.insert_at - 1]
            pending.setdefault(mark.insert_at, []).append((verse_at, mark))

        parts: list[str] = []
        curr_red: bool | None = None
        curr_txt: list[str] = []

        def flush_buf() -> None:
            if not curr_txt:
                return
            merged = "".join(curr_txt)
            if curr_red:
                parts.append(
                    '<span style="color:#FF0000">'
                    f"{html.escape(merged, quote=False)}</span>"
                )
            else:
                parts.append(merged)
            curr_txt.clear()

        def append_char(ch: str, red: bool) -> None:
            nonlocal curr_red
            if curr_txt and red != curr_red:
                flush_buf()
            curr_red = red
            curr_txt.append(ch)

        # An undertie at the end of the paragraph becomes a space. Drop it
        # so the call sits on the word (Acts 4:25).
        end = len(raw.rstrip())

        def emit_notes(pos: int) -> None:
            items = pending.pop(pos, [])
            if not items:
                return
            if pos >= end:
                while curr_txt and curr_txt[-1] == " ":
                    curr_txt.pop()
            flush_buf()
            for verse_at, mark in items:
                parts.append(self._notation_call(verse_at, mark))

        raw_pos = 0
        for event in events:
            if event[0] == "fn":
                emit_notes(raw_pos)
                flush_buf()
                curr_red = None
                hl_text = event[1]
                if len(hl_text) == 1 and hl_text.isalpha():
                    self.current_verse = event[2]
                    self.text_calls_map[hl_text] = self.current_verse
                    key = (
                        f"{self.current_book}_{self.current_chapter}_"
                        f"{self.current_verse}_{hl_text}"
                    )
                    parts.append(f"[^{key}]")
                continue
            _kind, r_text, red, run_verse = event
            self.current_verse = run_verse
            for ch in r_text:
                emit_notes(raw_pos)
                raw_pos += 1
                # The star is a spelling flag, not a letter and not a footnote.
                if ch in {ARROW, BAR, "*"}:
                    continue
                if ch == TIE:
                    ch = " "
                append_char(ch, red)
        emit_notes(raw_pos)
        flush_buf()
        if pending:
            raise SystemExit(f"notation notes not placed: {sorted(pending)}")
        return "".join(parts).replace("\xa0", " ")

    def convert(self) -> str:
        self.lines.append(PROVENANCE_COMMENT.rstrip())
        self.lines.append("")

        paragraphs = self.doc.paragraphs
        for para_index, para in enumerate(paragraphs):
            txt = para.text.strip()
            if not txt:
                continue

            style_name = para.style.name if para.style else "Normal"

            # ── 1. Books ───────────────────────────────────────────────
            if style_name == "Heading 1":
                self.flush_chapter()
                self.current_book = txt.replace(" ", "_")
                self.current_chapter = ""
                self.current_verse = ""
                self.started = True
                if self.lines and self.lines[-1] != "":
                    self.lines.append("")
                self.lines.append(f"# {txt}")
                self.lines.append("")
                self.last_was_indented = False
                continue

            if not self.started:
                continue

            # ── 2. Chapters ────────────────────────────────────────────
            if style_name == "Heading 2":
                self.flush_chapter()
                m = re.search(r"(\d+)$", txt)
                self.current_chapter = m.group(1) if m else txt
                self.current_verse = ""
                if self.lines and self.lines[-1] != "":
                    self.lines.append("")
                self.lines.append(f"## {txt}")
                self.lines.append("")
                self.last_was_indented = False
                continue

            # ── 3. Sections ────────────────────────────────────────────
            if style_name in ("Heading 3", "hdg"):
                if any(ch in txt for ch in (ARROW, BAR, TIE)):
                    raise SystemExit(f"notation mark in a heading: {txt}")
                title_part, ref_part = "", ""
                for r in para.runs:
                    r_txt = r.text
                    if not r_txt:
                        continue
                    if is_run_blue(r):
                        ref_part += r_txt
                    else:
                        title_part += r_txt

                title_part = title_part.strip()
                ref_part = ref_part.strip()

                if not ref_part:
                    m_ref = re.match(
                        r"^(.*?)\s*(\([A-Za-z0-9\s:;,\-–—]+\))\s*$", title_part
                    )
                    if m_ref:
                        title_part = m_ref.group(1).strip()
                        ref_part = m_ref.group(2).strip()

                if ref_part:
                    blue_ref = (
                        f'<span style="color:#0092F2">'
                        f"{html.escape(ref_part, quote=False)}</span>"
                    )
                    sec_line = f"### {title_part}<br>*{blue_ref}*"
                else:
                    sec_line = f"### {title_part}"

                if self.current_chapter:
                    self.chapter_verses.append(VerseLine("", is_heading=True))
                    self.chapter_verses.append(VerseLine(sec_line, is_heading=True))
                    self.chapter_verses.append(VerseLine("", is_heading=True))
                else:
                    if self.lines and self.lines[-1] != "":
                        self.lines.append("")
                    self.lines.append(sec_line)
                    self.lines.append("")
                self.last_was_indented = False
                continue

            # ── 4. Footnotes ───────────────────────────────────────────
            if re.match(r"^[a-z]\s+\d+", txt, re.IGNORECASE) or style_name == "foot":
                notes = parse_footnote_block(txt)
                for ltr, v_num, cnt in notes:
                    self.chapter_footnotes.append((ltr, v_num, cnt))
                continue

            # ── 5. Content ─────────────────────────────────────────────
            vm_head = re.match(r"^(\d+)[\s\xa0]", txt)
            if vm_head:
                self.current_verse = vm_head.group(1)

            content = self._render_paragraph(para, para_index, paragraphs)

            verse_lines = bold_and_split_verse_numbers(content)

            for vl in verse_lines:
                m_v = re.search(r"\*\*(\d+)\*\*", vl)
                if m_v:
                    self.current_verse = m_v.group(1)

            is_indented, nbsp_prefix = get_paragraph_indentation(para)

            for i, vl in enumerate(verse_lines):
                if is_indented:
                    line_str = f"> {nbsp_prefix}{vl}<br>"
                else:
                    line_str = vl

                if self.current_chapter:
                    if not (is_indented and self.last_was_indented) and i == 0:
                        if self.chapter_verses and self.chapter_verses[-1].text != "":
                            self.chapter_verses.append(
                                VerseLine("", verse_num=self.current_verse)
                            )
                    self.chapter_verses.append(
                        VerseLine(line_str, verse_num=self.current_verse)
                    )
                else:
                    if not (is_indented and self.last_was_indented) and i == 0:
                        if self.lines and self.lines[-1] != "":
                            self.lines.append("")
                    self.lines.append(line_str)

            self.last_was_indented = is_indented

        self.flush_chapter()

        result = "\n".join(self.lines)
        result = re.sub(r"\n{4,}", "\n\n\n", result)
        # Drop empty red spans left when a footnote call consumed the run
        result = re.sub(
            r'<span style="color:#FF0000">\s*</span>', "", result
        )
        # Collapse accidental ASCII multi-spaces in body text (&nbsp; untouched)
        result = re.sub(r" {2,}", " ", result)
        result = apply_compound_readings(result)
        result = apply_berean_errata(result)
        from apply_verse_completeness import apply as apply_verse_completeness
        from apply_protestant_coverage import apply as apply_protestant_coverage
        result = apply_verse_completeness(result)
        result = apply_protestant_coverage(result)
        result = hoist_markers_out_of_red(result)
        # After completeness: it still looks for U+0387, which NFC maps to U+00B7.
        result = nfc_outside_tags(result)
        return result.strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert prepared BGB DOCX into structured Markdown."
    )
    parser.add_argument("-i", "--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1

    print(f"Converting: {args.input}")
    print(f"Output    : {args.output}\n")

    converter = BGBConverter(args.input)
    markdown = converter.convert()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markdown, encoding="utf-8")

    print("OK — done")
    print(f"  Lines written: {markdown.count(chr(10)) + 1:,}")
    counts = converter.notation_counts
    print(
        f"  Notation notes: {counts['order']} word order, "
        f"{counts['compound']} compound"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
