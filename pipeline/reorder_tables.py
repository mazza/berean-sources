#!/usr/bin/env python3
"""
reorder_tables.py

Reorder archive/bsb_tables.tsv into original-language reading order
(Heb Sort → Greek Sort → BSB Sort) as extra/tables-original-order.tsv.

This token/morphology table is for interlinear and word-level work.
Continuous OT prose (prepared/hebrew-ot.md) is built separately from the
same archive TSV by hebrew_tsv_to_markdown.py — it does not require this file.

Defaults:
  input:  archive/bsb_tables.tsv
  output: extra/tables-original-order.tsv

Usage:
  python3 pipeline/reorder_tables.py
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from reading_errata import apply_hebrew_row, load_hebrew_errata

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT = ROOT / "archive" / "bsb_tables.tsv"
DEFAULT_OUTPUT = ROOT / "extra" / "tables-original-order.tsv"

SENTINEL = 10**12


def parse_sort(value: str) -> int:
    s = (value or "").strip()
    if not s:
        return SENTINEL
    try:
        return int(s)
    except ValueError:
        return SENTINEL


def find_col(header: list[str], name: str) -> int:
    target = name.strip().lower()
    for i, h in enumerate(header):
        if h.strip().lower() == target:
            return i
    # substring fallback
    for i, h in enumerate(header):
        if target in h.strip().lower():
            return i
    raise KeyError(name)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reorder archive/bsb_tables.tsv by Heb Sort → Greek Sort → BSB Sort "
            "into extra/tables-original-order.tsv."
        )
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Source TSV (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Destination TSV (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    # Defaults are absolute (from this file). Explicit relative paths use cwd.
    src = Path(args.input).expanduser()
    src = src.resolve() if src.is_absolute() else (Path.cwd() / src).resolve()
    dst = Path(args.output).expanduser()
    dst = dst.resolve() if dst.is_absolute() else (Path.cwd() / dst).resolve()

    if not src.is_file():
        print(f"[ERROR] Input not found: {src}", file=sys.stderr)
        return 1

    print(f"[INFO] Reading: {src}", file=sys.stderr)
    print(f"[INFO] Output : {dst}", file=sys.stderr)

    with src.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            print("[ERROR] Empty input", file=sys.stderr)
            return 1

        try:
            i_heb = find_col(header, "Heb Sort")
            i_grk = find_col(header, "Greek Sort")
            i_bsb = find_col(header, "BSB Sort")
        except KeyError as e:
            print(f"[ERROR] Missing column: {e}", file=sys.stderr)
            print(f"[ERROR] Header: {header[:12]}...", file=sys.stderr)
            return 1

        rows: list[list[str]] = []
        n_in = 0
        errata = load_hebrew_errata()
        for row in reader:
            n_in += 1
            if n_in % 200000 == 0:
                print(f"[INFO] … loaded {n_in} rows", file=sys.stderr)
            # pad short rows so sort indices never IndexError
            if len(row) <= max(i_heb, i_grk, i_bsb):
                row = row + [""] * (max(i_heb, i_grk, i_bsb) + 1 - len(row))
            rows.append(apply_hebrew_row(header, row, errata))

    print(f"[INFO] Rows loaded: {n_in}", file=sys.stderr)
    print("[INFO] Sorting by Heb Sort, Greek Sort, BSB Sort …", file=sys.stderr)

    def sort_key(row: list[str]) -> tuple[int, int, int]:
        return (
            parse_sort(row[i_heb] if i_heb < len(row) else ""),
            parse_sort(row[i_grk] if i_grk < len(row) else ""),
            parse_sort(row[i_bsb] if i_bsb < len(row) else ""),
        )

    rows.sort(key=sort_key)

    dst.parent.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Writing: {dst}", file=sys.stderr)

    with dst.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(
            f,
            delimiter="\t",
            lineterminator="\n",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writerow(header)
        n_out = 0
        for row in rows:
            writer.writerow(row)
            n_out += 1
            if n_out % 200000 == 0:
                print(f"[INFO] … wrote {n_out} rows", file=sys.stderr)

    print(f"[INFO] Done. Wrote {n_out} data rows (+ header).", file=sys.stderr)
    print(f"[INFO] Output file: {dst}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
