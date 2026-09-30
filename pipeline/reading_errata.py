"""Apply reading corrections while the prepared files are generated.

The archive download is left unchanged. Rules live in hebrew_errata.tsv.
"""

from __future__ import annotations

import csv
from pathlib import Path

ERRATA = Path(__file__).resolve().parent / "hebrew_errata.tsv"


def load_hebrew_errata(path: Path | None = None) -> list[dict[str, str]]:
    path = path or ERRATA
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle, delimiter="\t")
        ]


def apply_hebrew_row(
    header: list[str],
    row: list[str],
    rules: list[dict[str, str]] | None = None,
) -> list[str]:
    """Correct one tables row. ``set_sort`` runs after text replacements."""
    if "Heb Sort" not in header:
        return row
    rules = load_hebrew_errata() if rules is None else rules
    if not rules:
        return row
    index = header.index("Heb Sort")
    if index >= len(row):
        return row
    sort = row[index].strip()
    matched = [rule for rule in rules if rule.get("heb_sort") == sort]
    if not matched:
        return row
    for rule in matched:
        if rule.get("action") != "replace":
            continue
        old, new = rule.get("from", ""), rule.get("to", "")
        if not old:
            continue
        for cell in range(len(row)):
            if old in row[cell]:
                row[cell] = row[cell].replace(old, new)
    for rule in matched:
        if rule.get("action") == "set_sort" and rule.get("to"):
            row[index] = rule["to"]
    return row
