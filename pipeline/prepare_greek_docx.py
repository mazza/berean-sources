#!/usr/bin/env python3
"""
prepare_greek_docx.py

Prepare the original BGB DOCX (book/chapter headings, words of Jesus in red).

Defaults:
  input:  archive/bgb.docx
  output: prepared/_work/bgb-edited.docx

Usage:
    python3 pipeline/prepare_greek_docx.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

SCRIPT_DIR = Path(__file__).resolve().parent
BEREAN_ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT = BEREAN_ROOT / "archive" / "bgb.docx"
DEFAULT_OUTPUT = BEREAN_ROOT / "prepared" / "_work" / "bgb-edited.docx"

NT_BOOKS_SET = {
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians",
    "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon",
    "Hebrews", "James", "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John", "Jude", "Revelation",
}


def make_run_explicit_red(run) -> None:
    """Inject the XML tag <w:color w:val="FF0000"/> directly into the run element."""
    rPr = run._element.get_or_add_rPr()
    color = rPr.find(qn('w:color'))
    if color is None:
        color = OxmlElement('w:color')
        rPr.append(color)
    color.set(qn('w:val'), 'FF0000')


def prepare(input_path: Path, output_path: Path) -> None:
    print(f"Opening: {input_path}")
    doc = Document(str(input_path))

    stats = {"books": 0, "chapters": 0, "sections": 0, "red_runs": 0}

    for para in doc.paragraphs:
        txt = para.text.strip()
        p_style = para.style.name if para.style else ''

        # 1. Book title (Heading 1)
        if txt in NT_BOOKS_SET:
            para.style = doc.styles['Heading 1']
            stats["books"] += 1
            continue

        # 2. Chapter title (Heading 2)
        match = re.match(r"^(.*?)\s+(\d+)$", txt)
        if match and match.group(1) in NT_BOOKS_SET:
            para.style = doc.styles['Heading 2']
            stats["chapters"] += 1
            continue

        # 3. Section title (uses the native 'hdg' style label from bgb.docx)
        if p_style == 'hdg':
            para.style = doc.styles['Heading 3']
            stats["sections"] += 1
            continue

        # 4. Bake Jesus's red colors into the XML (as Google Docs does)
        is_para_red = 'red' in p_style.lower()

        for run in para.runs:
            is_run_red = False
            rPr = run._element.rPr
            if rPr is not None:
                rstyle = rPr.find(qn('w:rStyle'))
                if rstyle is not None:
                    val = rstyle.attrib.get(qn('w:val'))
                    if val and 'red' in val.lower():
                        is_run_red = True

            if is_para_red or is_run_red:
                make_run_explicit_red(run)
                stats["red_runs"] += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))

    print(f"\nOK — saved: {output_path}")
    print(f"  Books (Heading 1)     : {stats['books']}")
    print(f"  Chapters (Heading 2)  : {stats['chapters']}")
    print(f"  Sections (Heading 3)  : {stats['sections']}")
    print(f"  Red runs processed    : {stats['red_runs']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare BGB DOCX: Heading 1/2/3 and explicit red color baking."
    )
    parser.add_argument(
        "-i", "--input", type=Path, default=DEFAULT_INPUT,
        help=f"Input DOCX (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Output DOCX (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.input.is_file():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        return 1
    prepare(args.input, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
