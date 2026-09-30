#!/usr/bin/env python3
"""
Post-pass for greek-nt.md completeness (reproducible).

1. Promote classic critical-omission verses into the main flow from
   ``critical_verses.tsv`` (BYZ/TR/NE wording curated from BGB apparatus /
   standard free Byzantine-TR forms), with concise footnotes that state
   attestation without disparaging Scripture.
2. Fix bare verse numerals that already sit in the continuous text
   (e.g. ``15 [ἢ]`` → ``**15** [ἢ]``).
3. Special joins: John 5:3b; Acts 24:6b / 24:8a. One anchor note
   on the first fragment; the later fragments point at that note.

Called from ``greek_docx_to_markdown.py`` after the spelling errata.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VERSES_TSV = SCRIPT_DIR / "critical_verses.tsv"

# John 5:3b (often bundled with 5:4 in apparatus)
JOHN_5_3B = "ἐκδεχομένων τὴν τοῦ ὕδατος κίνησιν."
# Acts 24:6b / 8a (with verse 7 in critical_verses.tsv)
ACTS_24_6B = "καὶ κατὰ τὸν ἡμέτερον νόμον ἠθελήσαμεν κρῖναι."
ACTS_24_8A = "κελεύσας τοὺς κατηγόρους αὐτοῦ ἔρχεσθαι ἐπὶ σέ·"
_SEE_JOHN_5 = "See note on v. 3."
_SEE_ACTS_24 = "See note on v. 6."


def load_critical_verses(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def fn_key(book: str, ch: int, v: int, letter: str = "t") -> str:
    return f"{book.replace(' ', '_')}_{ch}_{v}_{letter}"


def _flow_only(chapter_body: str) -> str:
    """Mask footnote definition lines (same length) so apparatus digits ≠ markers."""

    def _mask(m: re.Match[str]) -> str:
        return " " * len(m.group(0))

    return re.sub(r"^\[\^[^\]]+\]:.*$", _mask, chapter_body, flags=re.M)


def has_verse_marker(chapter_body: str, v: int) -> bool:
    """True if verse ``v`` is a real flow marker (mid-line OK; footnote defs ignored)."""
    return bool(re.search(rf"(?<!\d)\*\*{v}\*\*", _flow_only(chapter_body)))


def _marker_spans(chapter_body: str) -> list[tuple[int, int, int]]:
    """List of (verse_num, start, end) for ``**N**`` markers in flow text only."""
    flow = _flow_only(chapter_body)
    return [
        (int(m.group(1)), m.start(), m.end())
        for m in re.finditer(r"(?<!\d)\*\*(\d+)\*\*", flow)
    ]


def insert_verse_after(
    chapter_body: str, after_v: int, new_v: int, greek: str, book: str, ch: int
) -> str:
    """Insert **new_v** with the preceding verse, before a heading that sits in between.

    The next ``**N**`` can fall after a section heading. The restored verse
    belongs with ``after_v`` (Matthew 17:21, Mark 11:26, Romans 16:24).
    """
    if has_verse_marker(chapter_body, new_v):
        return chapter_body
    key = fn_key(book, ch, new_v, "t")
    spans = _marker_spans(chapter_body)
    after_idx = next((i for i, (n, _, _) in enumerate(spans) if n == after_v), None)
    if after_idx is None:
        return chapter_body
    insertion = f"\n\n**{new_v}** {greek}[^{key}]\n\n"
    if after_idx + 1 < len(spans):
        next_at = spans[after_idx + 1][1]
        between = chapter_body[spans[after_idx][2] : next_at]
    else:
        between = chapter_body[spans[after_idx][2] :]
        next_at = len(chapter_body)
    heading = re.search(r"\n+(?=### )", between)
    footnote = re.search(r"\n\[\^", between)
    if heading and (footnote is None or heading.start() < footnote.start()):
        start = spans[after_idx][2] + heading.start()
        end = spans[after_idx][2] + heading.end()
        return chapter_body[:start] + insertion + chapter_body[end:]
    if after_idx + 1 < len(spans):
        insert_at = next_at
    else:
        cut = len(between)
        if footnote:
            cut = footnote.start()
        insert_at = spans[after_idx][2] + cut
    return chapter_body[:insert_at] + insertion + chapter_body[insert_at:]


def replace_or_add_fn(md: str, key: str, note: str) -> str:
    """Replace existing footnote def for key, or append after the last footnote def."""
    def_pat = re.compile(rf"^\[\^{re.escape(key)}\]:\s*.*$", re.M)
    line = f"[^{key}]: {note}"
    if def_pat.search(md):
        return def_pat.sub(line, md, count=1)
    matches = list(re.finditer(r"^\[\^[^\]]+\]:.*$", md, re.M))
    if matches:
        pos = matches[-1].end()
        return md[:pos] + "\n" + line + md[pos:]
    return md + "\n" + line + "\n"


def _witness_label(text: str) -> str:
    """Sigla named before the included Greek, in the source's order."""
    head = re.split(
        r"\binclude\b|\d+\s+[\u0370-\u03FF\u1F00-\u1FFF]",
        text,
        maxsplit=1,
        flags=re.I,
    )[0]
    seen: list[str] = []
    for part in re.findall(r"\b(?:NE|NA|SBL|WH|BYZ|TR|GOC)\b", head, re.I):
        label = part.upper()
        if label not in seen:
            seen.append(label)
    return "/".join(seen) if seen else "BYZ/TR"


def shorten_neighbor_include_fn(md: str, book: str, ch: int, v: int) -> str:
    """
    Shorten BGB apparatus footnotes on neighboring verses that quoted the
    restored verse Greek under ``BYZ and TR include …``.

    Never touches ``*_t`` keys (our restored-verse notes).
    A leading ``See …`` stays. A note that only quoted the restored verse
    is removed, call and definition: that verse already carries the attestation.
    """
    bk = book.replace(" ", "_")
    dropped: list[str] = []
    for vv in (v - 1, v, v + 1):
        for letter in "abcdefghijklmnopqrstuvwxyz":
            if letter == "t":
                continue
            key = f"{bk}_{ch}_{vv}_{letter}"
            pat = re.compile(rf"^\[\^{re.escape(key)}\]:\s*(.+)$", re.M)

            def _sub(m: re.Match[str], _v: int = v, _key: str = key) -> str:
                text = m.group(1)
                # Bundled John 5:3 / Acts 24:6 handled separately
                if _key in ("John_5_3_a", "Acts_24_6_a"):
                    return m.group(0)
                # The See-clause is the widow parallel, now carried by 23:14.
                # BYZ 14 is this kingdom woe, without δέ, not the widow sentence.
                if _key == "Matthew_23_13_b":
                    return (
                        "[^Matthew_23_13_b]: BYZ numbers this woe as 14, without δέ: "
                        "Οὐαὶ ὑμῖν, γραμματεῖς καὶ Φαρισαῖοι, ὑποκριταί, ὅτι κλείετε "
                        "τὴν βασιλείαν τῶν οὐρανῶν ἔμπροσθεν τῶν ἀνθρώπων· ὑμεῖς γὰρ "
                        "οὐκ εἰσέρχεσθε, οὐδὲ τοὺς εἰσερχομένους ἀφίετε εἰσελθεῖν. "
                        "TR is similar."
                    )
                # "include 11", "include11", "BYZ and TR 44", "BYZ 14 Greek…"
                cites_v = bool(
                    re.search(
                        rf"(?:include\s*{_v}\b|include{_v}\b)|"
                        rf"(?:BYZ|TR|NE|SBL|WH)\b.{{0,60}}\b{_v}\s+"
                        rf"[\u0370-\u03FF\u1F00-\u1FFF]",
                        text,
                        re.I,
                    )
                )
                if not cites_v:
                    return m.group(0)

                see = re.match(r"(See [^.]+)\.", text)
                if see:
                    return f"[^{_key}]: {see.group(1)}."

                # Keep leading cross-ref sentences; drop the apparatus Greek dump
                before = re.split(
                    r"(?:BYZ|TR|NE|SBL|WH)\b.*(?:include\b|\b" + str(_v) + r"\b)",
                    text,
                    maxsplit=1,
                    flags=re.I,
                )
                head = before[0].strip(" .;")
                if head and "include" not in head.lower():
                    return f"[^{_key}]: {head}."
                # The call sat on the previous verse only because this one was absent.
                dropped.append(_key)
                return m.group(0)

            md = pat.sub(_sub, md)
    for key in dict.fromkeys(dropped):
        md = re.sub(
            rf"^\[\^{re.escape(key)}\]:.*(?:\n)?",
            "",
            md,
            count=1,
            flags=re.M,
        )
        md = re.sub(rf"\[\^{re.escape(key)}\](?!:)", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md


def fix_bare_verse_numerals(chapter_body: str) -> str:
    """Turn bare verse numbers in Greek flow into **N** markers.

    Skips footnote *definition* lines (``[^key]: …``), where apparatus often
    quotes ``4 ἄγγελος…`` / ``7 Παρελθὼν…`` — bolding those would create false
    verse markers and block restoration.
    """
    # BGB often drops **N** mid-flow after punctuation, HTML `>`, or a Greek word.
    pats = [
        re.compile(
            r"(?<=[··;:,.!?”’»\)>])\s*(\d{1,3})\s+(?=[\u0370-\u03FF\u1F00-\u1FFF\[<])"
        ),
        re.compile(
            r"(?<=[\u0370-\u03FF\u1F00-\u1FFF])\s+(\d{1,3})\s+(?=[\u0370-\u03FF\u1F00-\u1FFF])"
        ),
    ]
    out: list[str] = []
    for line in chapter_body.split("\n"):
        if re.match(r"^\[\^[^\]]+\]:", line):
            out.append(line)
            continue
        for pat in pats:
            line = pat.sub(lambda m: f" **{m.group(1)}** ", line)
        out.append(line)
    return "\n".join(out)


def apply_to_chapter(
    chapter_body: str, book: str, ch: int, verses: list[dict[str, str]]
) -> tuple[str, list[tuple[str, str]]]:
    """Returns updated chapter body and list of (fn_key, note) to ensure."""
    fns: list[tuple[str, str]] = []
    body = fix_bare_verse_numerals(chapter_body)
    for row in verses:
        if row["book"] != book or int(row["chapter"]) != ch:
            continue
        v = int(row["verse"])
        greek = row["greek"].rstrip()
        note = row["note"]
        key = fn_key(book, ch, v, "t")
        if has_verse_marker(body, v):
            # The verse is already in this chapter. Attach the note.
            if f"[^{key}]" not in body:
                body = re.sub(
                    rf"((?<!\d)\*\*{v}\*\*[^\n]*?)(\n\n|\n(?=\*\*)|\Z)",
                    rf"\1[^{key}]\2",
                    body,
                    count=1,
                )
            fns.append((key, note))
            continue
        if has_verse_marker(body, v - 1):
            body = insert_verse_after(body, v - 1, v, greek, book, ch)
        elif has_verse_marker(body, v + 1):
            spans = _marker_spans(body)
            nxt = next((s for s in spans if s[0] == v + 1), None)
            if nxt is None:
                raise RuntimeError(f"{book} {ch}:{v} could not be placed")
            insertion = f"\n\n**{v}** {greek}[^{key}]\n\n"
            body = body[: nxt[1]] + insertion + body[nxt[1] :]
        else:
            raise RuntimeError(f"{book} {ch}:{v} could not be placed")
        fns.append((key, note))
    return body, fns


def special_john_5(chapter_body: str) -> tuple[str, list[tuple[str, str]]]:
    """Insert 5:3b without a second call. The Berean note on verse 3 is the anchor."""
    spans = _marker_spans(chapter_body)
    s3 = next((s for s in spans if s[0] == 3), None)
    if not s3:
        return chapter_body, []
    next_start = next((s[1] for s in spans if s[0] in (4, 5)), len(chapter_body))
    block = chapter_body[s3[1] : next_start]
    if JOHN_5_3B.split()[0] not in block:
        block = block.rstrip().rstrip(" ,") + " " + JOHN_5_3B + "\n\n"
        chapter_body = chapter_body[: s3[1]] + block + chapter_body[next_start:]
    return chapter_body, []


def special_acts_24(chapter_body: str) -> tuple[str, list[tuple[str, str]]]:
    """Insert 6b without its own call. Verse 8a keeps one call that points at verse 6."""
    fns: list[tuple[str, str]] = []
    spans = _marker_spans(chapter_body)
    s6 = next((s for s in spans if s[0] == 6), None)
    if s6:
        next_start = next((s[1] for s in spans if s[0] in (7, 8)), len(chapter_body))
        block = chapter_body[s6[1] : next_start]
        if "ἡμέτερον νόμον" not in block:
            block = block.rstrip().rstrip(",") + " " + ACTS_24_6B + "\n\n"
            chapter_body = chapter_body[: s6[1]] + block + chapter_body[next_start:]

    spans = _marker_spans(chapter_body)
    s8 = next((s for s in spans if s[0] == 8), None)
    if not s8:
        return chapter_body, fns
    next_start = next((s[1] for s in spans if s[1] > s8[1]), len(chapter_body))
    key8 = "Acts_24_8_t"
    block = chapter_body[s8[2] : next_start]
    if "κελεύσας" not in block:
        insert_at = s8[2]
        while insert_at < len(chapter_body) and chapter_body[insert_at] in " \t":
            insert_at += 1
        chapter_body = (
            chapter_body[:insert_at]
            + ACTS_24_8A
            + f"[^{key8}] "
            + chapter_body[insert_at:]
        )
    elif f"[^{key8}]" not in block:
        at = chapter_body.find(ACTS_24_8A, s8[2])
        if at != -1 and at < next_start:
            at += len(ACTS_24_8A)
            chapter_body = chapter_body[:at] + f"[^{key8}]" + chapter_body[at:]
    fns.append((key8, _SEE_ACTS_24))
    return chapter_body, fns


def apply(md: str, verses_path: Path = VERSES_TSV) -> str:
    verses = load_critical_verses(verses_path)
    by_book_ch: dict[tuple[str, int], list[dict[str, str]]] = {}
    for row in verses:
        key = (row["book"], int(row["chapter"]))
        by_book_ch.setdefault(key, []).append(row)

    out_parts: list[str] = []
    pos = 0
    all_fns: list[tuple[str, str]] = []
    touched: list[tuple[str, int, int]] = []

    for m in re.finditer(r"^## (.+?) (\d+)\s*$", md, re.M):
        out_parts.append(md[pos : m.start()])
        book = m.group(1).strip()
        ch = int(m.group(2))
        rest = md[m.end() :]
        m2 = re.search(r"\n(?=## |# )", rest)
        body = rest[: m2.start()] if m2 else rest
        tail_start = m.end() + (m2.start() if m2 else len(rest))
        header = m.group(0)
        body2, fns = apply_to_chapter(body, book, ch, by_book_ch.get((book, ch), []))
        if book == "John" and ch == 5:
            body2, fns2 = special_john_5(body2)
            fns.extend(fns2)
        if book == "Acts" and ch == 24:
            body2, fns2 = special_acts_24(body2)
            fns.extend(fns2)
        all_fns.extend(fns)
        for row in by_book_ch.get((book, ch), []):
            touched.append((book, ch, int(row["verse"])))
        out_parts.append(header + body2)
        pos = tail_start

    md_out = "".join(out_parts) + md[pos:]

    # John 5:3a / Acts 24:6a often bundled 3b+4 / 6b+7+8a — shorten those first
    md_out = _shorten_bundled_fn(
        md_out,
        "John_5_3_a",
        "Also attested in NE/BYZ/TR; many early MSS lack the rest of verse 3 and verse 4.",
    )
    md_out = _shorten_bundled_fn(
        md_out,
        "Acts_24_6_a",
        "Also attested in BYZ/TR; many early MSS lack the rest of verse 6 through the opening of verse 8.",
    )

    for book, ch, v in touched:
        md_out = shorten_neighbor_include_fn(md_out, book, ch, v)

    # Deduplicate fns (last note wins)
    seen: dict[str, str] = {}
    for key, note in all_fns:
        seen[key] = note
    for key, note in seen.items():
        md_out = replace_or_add_fn(md_out, key, note)

    # The restored verses keep their calls. The attestation lives on the anchor.
    md_out = _shorten_bundled_fn(md_out, "John_5_4_t", _SEE_JOHN_5)
    md_out = _shorten_bundled_fn(md_out, "Acts_24_7_t", _SEE_ACTS_24)
    md_out = _shorten_bundled_fn(md_out, "Acts_24_8_t", _SEE_ACTS_24)

    md_out = re.sub(r"\n{3,}", "\n\n", md_out)
    return md_out


def _shorten_bundled_fn(md: str, key: str, note: str) -> str:
    """Replace a long bundled-include footnote with a short attestation note."""
    pat = re.compile(rf"^\[\^{re.escape(key)}\]:\s*.*$", re.M)
    if not pat.search(md):
        raise RuntimeError(f"missing footnote {key}")
    return pat.sub(f"[^{key}]: {note}", md, count=1)


