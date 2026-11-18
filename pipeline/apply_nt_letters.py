#!/usr/bin/env python3
"""Put embedded New Testament letters in one blockquote.

The Greek download already prints the prescript on its own lines. This step
runs after the other Greek edits and only adds the Markdown used for the
same letters in the VFE: the address stays outside, and the body is one
blockquote. It does not change a Greek word.

Acts 15 and Acts 23 are the letters copied inside the narrative. Revelation
2–3 are the seven messages: ``γράψον`` stays outside, and ``Τάδε λέγει``
through the hearing formula is the body. James 1 is the book itself and is
left as it is.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GREEK = ROOT / "prepared" / "greek-nt.md"


def _norm(text: str) -> str:
    lines = [re.sub(r"^(?:>\s*)+", "", line) for line in text.splitlines()]
    return re.sub(r"\s+", " ", "\n".join(lines)).strip()


def _quote(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        if line == "":
            out.append(">")
        elif line.startswith(">"):
            out.append(line)
        else:
            out.append("> " + line)
    return out


def _find(lines: list[str], exact: str, start: int = 0) -> int:
    for index in range(start, len(lines)):
        if lines[index] == exact:
            return index
    return -1


def _wrap_span(lines: list[str], start: int, end: int) -> None:
    """Quote lines[start:end], inclusive. ``end`` is exclusive."""
    while start < end and lines[start] == "":
        start += 1
    while end > start and lines[end - 1] == "":
        end -= 1
    if start >= end or lines[start].startswith(">"):
        return
    lines[start:end] = _quote(lines[start:end])


def _wrap_acts(lines: list[str]) -> None:
    """Greeting through the close, after the prescript that is already outside."""
    jerusalem = _find(lines, "**23** γράψαντες διὰ χειρὸς αὐτῶν")
    if jerusalem < 0:
        raise SystemExit("Acts 15 letter introduction was not found")
    greeting = _find(lines, "Χαίρειν.", jerusalem)
    if greeting >= 0 and greeting - jerusalem <= 12:
        close = _find(lines, "Ἔρρωσθε.”", greeting)
        if close < 0:
            raise SystemExit("Acts 15 letter close was not found")
        _wrap_span(lines, greeting, close + 1)
    elif _find(lines, "> Χαίρειν.", jerusalem) - jerusalem > 12:
        raise SystemExit("Acts 15 greeting was not found")

    lysias = _find(lines, "**26** “Κλαύδιος Λυσίας")
    if lysias < 0:
        raise SystemExit("Acts 23 prescript was not found")
    greeting = _find(lines, "Χαίρειν.", lysias)
    # James 1 also opens with Χαίρειν. Only the greeting of this prescript counts.
    if greeting < 0 or greeting - lysias > 12:
        quoted = _find(lines, "> Χαίρειν.", lysias)
        if quoted < 0 or quoted - lysias > 12:
            raise SystemExit("Acts 23 greeting was not found")
        return
    close = _find(
        lines,
        "**30** Μηνυθείσης δέ μοι ἐπιβουλῆς εἰς τὸν ἄνδρα ἔσεσθαι, ἐξαυτῆς ἔπεμψα πρὸς σέ, παραγγείλας καὶ τοῖς κατηγόροις λέγειν [τὰ] πρὸς αὐτὸν ἐπὶ σοῦ.”",
        greeting,
    )
    if close < 0:
        close = _find(
            lines,
            "> **30** Μηνυθείσης δέ μοι ἐπιβουλῆς εἰς τὸν ἄνδρα ἔσεσθαι, ἐξαυτῆς ἔπεμψα πρὸς σέ, παραγγείλας καὶ τοῖς κατηγόροις λέγειν [τὰ] πρὸς αὐτὸν ἐπὶ σοῦ.”",
            greeting,
        )
    if close < 0:
        raise SystemExit("Acts 23 letter close was not found")
    _wrap_span(lines, greeting, close + 1)


def _wrap_revelation(lines: list[str]) -> int:
    """Seven messages. The ``write`` line stays outside; the dictated text does not."""
    wrapped = 0
    index = 0
    while index < len(lines):
        if "ἐκκλησίας γράψον</span>" not in lines[index]:
            index += 1
            continue
        body = index + 1
        if body < len(lines) and lines[body] == "":
            body += 1
        end = body
        while end < len(lines) and not (
            lines[end].startswith("### ")
            or lines[end].startswith("## ")
            or lines[end].startswith("[^")
        ):
            end += 1
        if body < end and not lines[body].startswith(">"):
            _wrap_span(lines, body, end)
            wrapped += 1
        index = end
    if wrapped not in {0, 7}:
        raise SystemExit(f"expected 7 Revelation letters, wrapped {wrapped}")
    return wrapped


def apply(text: str) -> str:
    before = _norm(text)
    lines = text.splitlines()
    _wrap_acts(lines)
    letters = _wrap_revelation(lines)
    if letters not in {0, 7}:
        raise SystemExit(f"expected 7 Revelation letters, wrapped {letters}")
    result = "\n".join(lines)
    if text.endswith("\n"):
        result += "\n"
    after = _norm(result)
    if before != after:
        raise SystemExit("letter layout changed Greek words")
    return result


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GREEK
    original = path.read_text(encoding="utf-8")
    path.write_text(apply(original), encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
