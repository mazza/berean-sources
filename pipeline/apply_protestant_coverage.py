#!/usr/bin/env python3
"""Put Protestant verse coverage into the Greek Markdown.

Runs after the Berean text is built. It does not edit archive/bgb.docx.

- 3 John 15 and Revelation 12:18 already have their sentences; they gain
  the verse number used by Protestant English editions.
- 1 John 5:7–8 gains the heavenly witnesses. The words match Scrivener
  1894 (public domain); the accents are filled in.
- A Berean note that says the Textus Receptus or the Byzantine text
  includes a Greek clause is copied into that verse when the clause is
  not already there. Once the clause is in the verse, the note records
  attestation instead of saying "include".
- A restored clause or verse that continues words of Jesus is marked with
  the same red span Berean uses for his speech. Narrative restorations
  stay as printed.
- The clause is then seated in the sentence or the poem around it. A new
  colon takes that poem's indent, and a period or quotation mark that
  closed the shorter reading moves to the true end. Acts 8:37 quotes
  Philip and the eunuch.
"""

from __future__ import annotations

import re
import unicodedata

GREEK_LETTER = re.compile(r"[\u0370-\u03FF\u1F00-\u1FFF]")
NOTE_RE = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$", re.M)
CALL_RE_TMPL = r"\[\^{}\](?!:)"
INCLUDE_RE = re.compile(r"include\s+(.+)$", re.I)

COMMA_OLD = (
    "**7** ὅτι τρεῖς εἰσιν οἱ μαρτυροῦντες,[^1_John_5_7_a]\n"
    "**8** τὸ Πνεῦμα καὶ τὸ ὕδωρ καὶ τὸ αἷμα, καὶ οἱ τρεῖς εἰς τὸ ἕν εἰσιν."
)
# Scrivener 1894, 1 John 5:7–8, with accents supplied.
COMMA_NOTE = (
    "[^1_John_5_7_a]: Also attested in TR/GOC; many early MSS read only "
    "the earthly witnesses in v. 8."
)
COMMA_NOTE_RE = re.compile(r"^\[\^1_John_5_7_a\]:.*$", re.M)
COMMA_NEW = (
    "**7** ὅτι τρεῖς εἰσιν οἱ μαρτυροῦντες ἐν τῷ οὐρανῷ, "
    "ὁ Πατήρ, ὁ Λόγος, καὶ τὸ Ἅγιον Πνεῦμα· καὶ οὗτοι οἱ τρεῖς ἕν εἰσιν."
    "[^1_John_5_7_a]\n"
    "**8** καὶ τρεῖς εἰσιν οἱ μαρτυροῦντες ἐν τῇ γῇ, "
    "τὸ Πνεῦμα καὶ τὸ ὕδωρ καὶ τὸ αἷμα, καὶ οἱ τρεῖς εἰς τὸ ἕν εἰσιν."
)


def fold(text: str) -> list[str]:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ς", "σ").lower()
    return re.findall(r"[α-ω]+", text)


def polish(phrase: str) -> str:
    words = [tok for tok in phrase.split() if GREEK_LETTER.search(tok)]
    phrase = " ".join(words)
    phrase = phrase.replace("τὴς ", "τῆς ").replace("τὴς", "τῆς")
    phrase = _greek_homoglyphs(phrase)
    return phrase.strip()


def near(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    longer, shorter = (a, b) if len(a) > len(b) else (b, a)
    return any(longer[:i] + longer[i + 1 :] == shorter for i in range(len(longer)))


def already_covered(verse: str, phrase: str) -> bool:
    have = fold(verse)
    need = fold(phrase)
    if not need:
        return True
    missing = []
    pool = have[:]
    for word in need:
        hit = next((i for i, got in enumerate(pool) if got == word or near(got, word)), None)
        if hit is None:
            missing.append(word)
        else:
            pool.pop(hit)
    return not missing


def verse_bounds(text: str, call_at: int) -> tuple[int, int]:
    marks = list(re.finditer(r"\*\*\d+\*\*", text))
    start = 0
    end = len(text)
    for index, mark in enumerate(marks):
        if mark.start() <= call_at:
            start = mark.start()
            if index + 1 < len(marks):
                end = marks[index + 1].start()
        else:
            break
    return start, end


def insert_clause(text: str, note_id: str, phrase: str) -> str:
    call = f"[^{note_id}]"
    match = re.search(re.escape(call) + r"(?!:)", text)
    if not match:
        return text
    start, end = verse_bounds(text, match.start())
    if already_covered(text[start:end], phrase):
        return text
    piece = phrase.strip()
    # A final ASCII period here is the English note's sentence stop.
    # Keep it when the verse ends; drop it when Greek continues after the call.
    rest = text[match.end() :].lstrip()
    if piece.endswith(".") and rest[:1] and GREEK_LETTER.search(rest[0]):
        piece = piece[:-1].rstrip()
        if piece and piece[-1] not in ",;:··":
            piece += ","
    previous = text[match.start() - 1] if match.start() else ""
    gap = "" if previous.isspace() else " "
    return text[: match.start()] + gap + piece + " " + text[match.start() :]


def number_three_john(text: str) -> str:
    old = (
        "**14** ἐλπίζω δὲ εὐθέως σε ἰδεῖν, καὶ στόμα πρὸς στόμα λαλήσομεν.\n\n"
        "Εἰρήνη σοι.\n\n"
        "Ἀσπάζονταί σε οἱ φίλοι.\n\n"
        "Ἀσπάζου τοὺς φίλους κατ’ ὄνομα."
    )
    new = (
        "**14** ἐλπίζω δὲ εὐθέως σε ἰδεῖν, καὶ στόμα πρὸς στόμα λαλήσομεν.\n"
        "**15** Εἰρήνη σοι. Ἀσπάζονταί σε οἱ φίλοι. "
        "Ἀσπάζου τοὺς φίλους κατ’ ὄνομα."
    )
    found = text.count(old)
    if found != 1:
        raise RuntimeError(f"3 John 15: expected the unnumbered ending once, found {found}")
    return text.replace(old, new, 1)


def number_revelation_sand(text: str) -> str:
    old = "Καὶ ἐστάθη ἐπὶ τὴν ἄμμον τῆς θαλάσσης.[^Revelation_12_17_b]"
    new = "**18** Καὶ ἐστάθη ἐπὶ τὴν ἄμμον τῆς θαλάσσης.[^Revelation_12_18_b]"
    if text.count(old) != 1:
        raise RuntimeError("Revelation 12:18: expected the unnumbered sentence once")
    text = text.replace(old, new, 1)
    key = "[^Revelation_12_17_b]:"
    if text.count(key) != 1:
        raise RuntimeError("Revelation 12:18: expected the verse 17 note once")
    return text.replace(key, "[^Revelation_12_18_b]:", 1)


def cover_noted_clauses(text: str) -> str:
    for note_id, body in NOTE_RE.findall(text):
        if note_id == "1_John_5_7_a":
            continue
        if not re.search(r"\bTR\b", body) or "not include" in body.lower():
            continue
        if "include" not in body.lower():
            continue
        found = INCLUDE_RE.search(body)
        if not found:
            continue
        raw = found.group(1).strip()
        parts = re.split(r"\s+(?=\d+\s)", raw)
        phrase = polish(parts[0])
        if not fold(phrase):
            continue
        text = insert_clause(text, note_id, phrase)
        if len(parts) > 1 and note_id == "Luke_9_55_c":
            extra = polish(re.sub(r"^\d+\s+", "", parts[1]))
            call_at = text.find("[^Luke_9_55_c]")
            marker_at = text.find("**56**", call_at)
            if extra and marker_at != -1 and not already_covered(
                text[marker_at : marker_at + 500], extra
            ):
                rest = text[marker_at + 6 :]
                if not rest.startswith(" "):
                    rest = " " + rest
                text = text[:marker_at] + "**56** " + extra + rest
    return text


_LATIN_IN_GREEK = str.maketrans(
    {
        "A": "Α",
        "B": "Β",
        "E": "Ε",
        "H": "Η",
        "I": "Ι",
        "K": "Κ",
        "M": "Μ",
        "N": "Ν",
        "O": "Ο",
        "P": "Ρ",
        "T": "Τ",
        "X": "Χ",
        "Y": "Υ",
        "Z": "Ζ",
    }
)
_GLUED_ENGLISH = ("include", "BYZ", "SBL", "WH", "NA", "NE", "GOC", "TR")


def _greek_homoglyphs(text: str) -> str:
    """Turn a Latin lookalike into Greek when it sits inside a Greek word."""
    out: list[str] = []
    for tok in text.split(" "):
        if GREEK_LETTER.search(tok):
            tok = tok.translate(_LATIN_IN_GREEK)
        out.append(tok)
    return " ".join(out)


def _fix_note_token(tok: str) -> str:
    for prefix in _GLUED_ENGLISH:
        if tok.startswith(prefix) and len(tok) > len(prefix):
            nxt = tok[len(prefix)]
            if GREEK_LETTER.search(nxt):
                return prefix + " " + _greek_homoglyphs(tok[len(prefix) :])
    return _greek_homoglyphs(tok)


def _reading_slice(text: str, start: int, end: int) -> str:
    """Flow of the verse. Footnote lines and the next heading quote the clause too."""
    region = text[start:end]
    marker = re.search(r"^(?:\[\^|#)", region, re.M)
    if marker:
        region = region[: marker.start()]
    return region


def clause_in_reading(region: str, phrase: str) -> bool:
    """True when the note's Greek words sit in order in the verse."""
    have = fold(region)
    need = fold(phrase)
    if not need:
        return False
    width = len(need)
    for index in range(len(have) - width + 1):
        window = have[index : index + width]
        if all(got == want or near(got, want) for got, want in zip(window, need)):
            return True
    return False


def reword_body_includes(text: str) -> str:
    """A clause already printed in the verse is not 'included' by the note."""
    from apply_verse_completeness import _witness_label

    def repl(match: re.Match[str]) -> str:
        note_id, body = match.group(1), match.group(2)
        if note_id == "1_John_5_7_a":
            return match.group(0)
        low = body.lower()
        if "not include" in low or "include" not in low:
            return match.group(0)
        if not re.search(r"\bTR\b", body):
            return match.group(0)
        found = INCLUDE_RE.search(body)
        if not found:
            return match.group(0)
        raw = found.group(1).strip()
        parts = re.split(r"\s+(?=\d+\s)", raw)
        phrase = polish(parts[0])
        if not fold(phrase):
            return match.group(0)
        call = re.search(re.escape(f"[^{note_id}]") + r"(?!:)", text)
        if not call:
            return match.group(0)
        start, end = verse_bounds(text, call.start())
        if note_id == "Luke_9_55_c":
            end = min(len(text), start + 1200)
        region = _reading_slice(text, start, end)
        if note_id == "Luke_9_55_c":
            extras = [phrase]
            if len(parts) > 1:
                extras.append(polish(re.sub(r"^\d+\s+", "", parts[1])))
            covered = [item for item in extras if fold(item)]
            if not covered or not all(
                clause_in_reading(region, item) for item in covered
            ):
                return match.group(0)
        elif not clause_in_reading(region, phrase):
            return match.group(0)
        label = _witness_label(body)
        if note_id == "Luke_9_55_c":
            sentence = (
                f"Also attested in {label}; many early MSS lack "
                "the rest of verse 55 and verse 56."
            )
        else:
            sentence = (
                f"Also attested in {label}; many early MSS lack this clause."
            )
        sig = re.search(r"\b(?:NE|NA|SBL|WH|BYZ|TR|GOC)\b", body)
        lead = body[: sig.start()].strip(" ;") if sig else ""
        if lead:
            if lead[-1] not in ".!?":
                lead += "."
            sentence = f"{lead} {sentence}"
        return f"[^{note_id}]: {sentence}"

    return NOTE_RE.sub(repl, text)


def tidy_note_definitions(md: str) -> str:
    """Orthography inside Berean note lines. The archive download is untouched."""

    def repl(match: re.Match[str]) -> str:
        body = match.group(2)
        body = re.sub(r"\binclude\s+include\b", "include", body, flags=re.I)
        body = body.replace("τὴς", "τῆς")
        body = " ".join(_fix_note_token(tok) for tok in body.split(" "))
        return f"[^{match.group(1)}]: {body}"

    return NOTE_RE.sub(repl, md)


RED = '<span style="color:#FF0000">'
END = "</span>"
# Berean quotation marks, and the middle dot NFC produces from ano teleia.
LQ = "\u2018"
RQ = "\u2019"
LD = "\u201c"
RD = "\u201d"
MDOT = "\u00b7"


def _nfc_outside_tags(text: str) -> str:
    """NFC the reading text. Completeness has already searched for U+0387."""
    parts = re.split(r"(<[^>\n]+>)", text)
    return "".join(
        part if part.startswith("<") else unicodedata.normalize("NFC", part)
        for part in parts
    )


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    found = text.count(old)
    if found != 1:
        raise RuntimeError(f"{label}: expected this wording once, found {found}")
    return text.replace(old, new, 1)


def _sub_once(text: str, pattern: re.Pattern[str], repl: str, label: str) -> str:
    updated, count = pattern.subn(repl, text, count=1)
    if count != 1:
        raise RuntimeError(f"{label}: expected this wording once, found {count}")
    if pattern.search(updated):
        raise RuntimeError(f"{label}: matched more than once")
    return updated


def redden_jesus_restorations(text: str) -> str:
    """Put restored words of Jesus inside Berean's red spans.

    The clauses are spliced in after the DOCX spans already closed, so a
    saying that Berean printed in red loses its restored continuation.
    Each edit below was read in place. A neighbor that is narrative, another
    speaker, or an epistle is not in this list: Matthew 28:9 and Luke 8:45
    sit next to red text and stay black, as do John 5:3b–4, Acts, and the
    letters.
    """
    text = _nfc_outside_tags(text)
    # (label, wording as spliced, wording inside the red span)
    edits: list[tuple[str, str, str]] = [
        (
            "Matthew 6:13",
            "Ἀλλὰ ῥῦσαι ἡμᾶς ἀπὸ τοῦ πονηροῦ."
            + RQ
            + f"{END} Ὅτι σοῦ ἐστιν ἡ βασιλεία καὶ ἡ δύναμις καὶ ἡ δόξα "
            "εἰς τοὺς αἰῶνας. Ἀμήν. [^Matthew_6_13_a]",
            "Ἀλλὰ ῥῦσαι ἡμᾶς ἀπὸ τοῦ πονηροῦ."
            + f"{END}<br>\n> {'&nbsp;' * 4}{RED}Ὅτι σοῦ ἐστιν ἡ βασιλεία "
            "καὶ ἡ δύναμις καὶ ἡ δόξα εἰς τοὺς αἰῶνας. Ἀμήν."
            + RQ
            + f"{END}[^Matthew_6_13_a]",
        ),
        (
            "Matthew 20:7",
            "Λέγει αὐτοῖς "
            + LQ
            + "Ὑπάγετε καὶ ὑμεῖς εἰς τὸν ἀμπελῶνα."
            + RQ
            + f"{END} καὶ ὃ ἐὰν ᾖ δίκαιον λήψεσθε. [^Matthew_20_7_b]",
            "Λέγει αὐτοῖς "
            + LQ
            + "Ὑπάγετε καὶ ὑμεῖς εἰς τὸν ἀμπελῶνα, καὶ ὃ ἐὰν ᾖ δίκαιον λήψεσθε."
            + RQ
            + f"{END}[^Matthew_20_7_b]",
        ),
        (
            "Matthew 20:16",
            "Οὕτως ἔσονται οἱ ἔσχατοι πρῶτοι καὶ οἱ πρῶτοι ἔσχατοι."
            + RD
            + f"{END} πολλοὶ γάρ εἰσιν κλητοί, ὀλίγοι δὲ ἐκλεκτοί. [^Matthew_20_16_c]",
            "Οὕτως ἔσονται οἱ ἔσχατοι πρῶτοι καὶ οἱ πρῶτοι ἔσχατοι. "
            "πολλοὶ γάρ εἰσιν κλητοί, ὀλίγοι δὲ ἐκλεκτοί."
            + RD
            + f"{END}[^Matthew_20_16_c]",
        ),
        (
            "Matthew 20:23",
            LD
            + "Τὸ μὲν ποτήριόν μου πίεσθε,"
            + f"{END} καὶ τὸ βάπτισμα ὃ ἐγὼ βαπτίζομαι βαπτισθήσεσθε "
            f"[^Matthew_20_23_e]{RED} τὸ δὲ καθίσαι",
            LD
            + "Τὸ μὲν ποτήριόν μου πίεσθε, καὶ τὸ βάπτισμα ὃ ἐγὼ βαπτίζομαι "
            f"βαπτισθήσεσθε{END}[^Matthew_20_23_e]{RED} τὸ δὲ καθίσαι",
        ),
        (
            "Matthew 25:13",
            "Γρηγορεῖτε οὖν, ὅτι οὐκ οἴδατε τὴν ἡμέραν οὐδὲ τὴν ὥραν."
            + f"{END} ἐν ᾗ ὁ υἱὸς τοῦ ἀνθρώπου ἔρχεται [^Matthew_25_13_a]",
            "Γρηγορεῖτε οὖν, ὅτι οὐκ οἴδατε τὴν ἡμέραν οὐδὲ τὴν ὥραν "
            f"ἐν ᾗ ὁ υἱὸς τοῦ ἀνθρώπου ἔρχεται.{END}[^Matthew_25_13_a]",
        ),
        (
            "Mark 6:11",
            "αὐτοῖς."
            + RD
            + f"{END} Ἀμὴν λέγω ὑμῖν, ἀνεκτότερον ἔσται Σοδόμοις ἢ Γομόρροις "
            "ἐν ἡμέρᾳ κρίσεως, ἢ τῇ πόλει ἐκείνῃ. [^Mark_6_11_a]",
            "αὐτοῖς. Ἀμὴν λέγω ὑμῖν, ἀνεκτότερον ἔσται Σοδόμοις ἢ Γομόρροις "
            "ἐν ἡμέρᾳ κρίσεως, ἢ τῇ πόλει ἐκείνῃ."
            + RD
            + f"{END}[^Mark_6_11_a]",
        ),
        (
            "Mark 7:8",
            "Ἀφέντες τὴν ἐντολὴν τοῦ Θεοῦ κρατεῖτε τὴν παράδοσιν τῶν ἀνθρώπων."
            + RD
            + f"{END} βαπτισμοὺς ξεστῶν καὶ ποτηρίων{MDOT} καὶ ἄλλα παρόμοια "
            "τοιαῦτα πολλὰ ποιεῖτε [^Mark_7_8_c]",
            "Ἀφέντες τὴν ἐντολὴν τοῦ Θεοῦ κρατεῖτε τὴν παράδοσιν τῶν ἀνθρώπων, "
            f"βαπτισμοὺς ξεστῶν καὶ ποτηρίων{MDOT} καὶ ἄλλα παρόμοια τοιαῦτα "
            "πολλὰ ποιεῖτε."
            + RD
            + f"{END}[^Mark_7_8_c]",
        ),
        (
            "Mark 9:49",
            "Πᾶς γὰρ πυρὶ ἁλισθήσεται."
            + f"{END} καὶ πᾶσα θυσία ἁλὶ ἁλισθήσεται. [^Mark_9_49_f]",
            "Πᾶς γὰρ πυρὶ ἁλισθήσεται. καὶ πᾶσα θυσία ἁλὶ ἁλισθήσεται."
            + f"{END}[^Mark_9_49_f]",
        ),
        (
            "Mark 13:14",
            "Ὅταν δὲ ἴδητε τὸ βδέλυγμα τῆς ἐρημώσεως"
            + f"{END} τὸ ῥηθὲν ὑπὸ Δανιὴλ τοῦ προφήτου "
            f"[^Mark_13_14_a]{RED} ἑστηκότα",
            "Ὅταν δὲ ἴδητε τὸ βδέλυγμα τῆς ἐρημώσεως τὸ ῥηθὲν ὑπὸ Δανιὴλ "
            f"τοῦ προφήτου{END}[^Mark_13_14_a]{RED} ἑστηκότα",
        ),
        (
            "Mark 13:33",
            f"Βλέπετε, ἀγρυπνεῖτε{MDOT}{END} καὶ προσεύχεσθε "
            f"[^Mark_13_33_e]{RED} οὐκ οἴδατε",
            f"Βλέπετε, ἀγρυπνεῖτε, καὶ προσεύχεσθε{MDOT}"
            + f"{END}[^Mark_13_33_e]{RED} οὐκ οἴδατε",
        ),
        (
            "Mark 14:27",
            LD
            + "Πάντες σκανδαλισθήσεσθε,"
            + f"{END} ἐν ἐμοὶ ἐν τῇ νυκτὶ ταύτῃ "
            f"[^Mark_14_27_e]{RED} ὅτι γέγραπται",
            LD
            + "Πάντες σκανδαλισθήσεσθε, ἐν ἐμοὶ ἐν τῇ νυκτὶ ταύτῃ"
            + f"{END}[^Mark_14_27_e]{RED} ὅτι γέγραπται",
        ),
        (
            "Luke 4:4",
            LD
            + "Γέγραπται ὅτι "
            + LQ
            + "Οὐκ ἐπ"
            + RQ
            + " ἄρτῳ μόνῳ ζήσεται ὁ ἄνθρωπος."
            + RQ
            + f"{END} ἀλλ"
            + RQ
            + " ἐπὶ παντὶ ῥήματι θεοῦ [^Luke_4_4_a]"
            + f"{RED}{RD}{END}",
            LD
            + "Γέγραπται ὅτι "
            + LQ
            + "Οὐκ ἐπ"
            + RQ
            + " ἄρτῳ μόνῳ ζήσεται ὁ ἄνθρωπος, ἀλλ"
            + RQ
            + " ἐπὶ παντὶ ῥήματι θεοῦ."
            + RQ
            + RD
            + f"{END}[^Luke_4_4_a]",
        ),
        (
            "Luke 4:18",
            "Ἀπέσταλκέν με"
            + f"{END} ἰάσασθαι τοὺς συντετριμμένους τὴν καρδίαν, "
            f"[^Luke_4_18_e]{RED} κηρῦξαι",
            f"Ἀπέσταλκέν με{END}<br>\n> {'&nbsp;' * 8}{RED}"
            "Ἰάσασθαι τοὺς συντετριμμένους τὴν καρδίαν,"
            + f"{END}[^Luke_4_18_e]<br>\n> {'&nbsp;' * 8}{RED}Κηρῦξαι",
        ),
        (
            "Luke 9:55",
            "**55** Στραφεὶς δὲ ἐπετίμησεν αὐτοῖς. καὶ εἴπεν, "
            "Οὐκ οἴδατε οἵου πνεύματός ἐστε ὑμεῖς [^Luke_9_55_c]\n"
            "**56** ὁ γὰρ υἱὸς τοῦ ἀνθρώπου οὐκ ἦλθεν ψυχὰς ἀνθρώπων ἀπολέσαι, "
            "ἀλλὰ σῶσαι. καὶ ἐπορεύθησαν εἰς ἑτέραν κώμην.",
            "**55** Στραφεὶς δὲ ἐπετίμησεν αὐτοῖς. καὶ εἴπεν, "
            + RED
            + LD
            + "Οὐκ οἴδατε οἵου πνεύματός ἐστε ὑμεῖς"
            + MDOT
            + f"{END}[^Luke_9_55_c]\n"
            "**56** "
            + RED
            + "ὁ γὰρ υἱὸς τοῦ ἀνθρώπου οὐκ ἦλθεν ψυχὰς ἀνθρώπων ἀπολέσαι, "
            "ἀλλὰ σῶσαι."
            + RD
            + f"{END}[^Luke_9_56_t] καὶ ἐπορεύθησαν εἰς ἑτέραν κώμην.",
        ),
        (
            "Luke 11:2",
            f"Ἐλθέτω ἡ βασιλεία σου{MDOT}{END} Γενηθήτω τὸ θέλημά σου, "
            "ὡς ἐν οὐρανῷ, καὶ ἐπὶ τῆς γῆς. [^Luke_11_2_b]"
            + f"{RED} τὸ {END}",
            f"Ἐλθέτω ἡ βασιλεία σου{MDOT}{END}<br>\n> {'&nbsp;' * 8}{RED}"
            f"Γενηθήτω τὸ θέλημά σου,{END}<br>\n> {'&nbsp;' * 8}{RED}"
            "Ὡς ἐν οὐρανῷ, καὶ ἐπὶ τῆς γῆς."
            + f"{END}[^Luke_11_2_b]",
        ),
        (
            "Luke 11:4",
            "Καὶ μὴ εἰσενέγκῃς ἡμᾶς εἰς πειρασμόν."
            + RQ
            + RD
            + f"{END} ἀλλὰ ῥῦσαι ἡμᾶς ἀπὸ τοῦ πονηροῦ [^Luke_11_4_c]",
            "Καὶ μὴ εἰσενέγκῃς ἡμᾶς εἰς πειρασμόν,"
            + f"{END}<br>\n> {'&nbsp;' * 8}{RED}"
            "Ἀλλὰ ῥῦσαι ἡμᾶς ἀπὸ τοῦ πονηροῦ."
            + RQ
            + RD
            + f"{END}[^Luke_11_4_c]",
        ),
        (
            "Luke 11:11",
            "Τίνα δὲ ἐξ ὑμῶν τὸν πατέρα αἰτήσει ὁ υἱὸς"
            + f"{END} ἄρτον, μὴ λίθον ἐπιδώσει αὐτῷ "
            f"[^Luke_11_11_d]{RED} ἰχθύν,",
            "Τίνα δὲ ἐξ ὑμῶν τὸν πατέρα αἰτήσει ὁ υἱὸς ἄρτον, μὴ λίθον ἐπιδώσει αὐτῷ"
            + f"{END}[^Luke_11_11_d]{RED} ἰχθύν,",
        ),
        (
            "Luke 12:39",
            "ὁ κλέπτης ἔρχεται,"
            + f"{END} ἐγρηγόρησεν ἄν, καὶ "
            f"[^Luke_12_39_e]{RED} οὐκ ἂν ἀφῆκεν",
            "ὁ κλέπτης ἔρχεται, ἐγρηγόρησεν ἄν, καὶ"
            + f"{END}[^Luke_12_39_e]{RED} οὐκ ἂν ἀφῆκεν",
        ),
        (
            "John 3:13",
            "ὁ Υἱὸς τοῦ ἀνθρώπου."
            + f"{END} ὁ ὢν ἐν τῷ οὐρανῷ [^John_3_13_b]",
            "ὁ Υἱὸς τοῦ ἀνθρώπου ὁ ὢν ἐν τῷ οὐρανῷ."
            + f"{END}[^John_3_13_b]",
        ),
        (
            "Matthew 18:11",
            "**11** Ἦλθεν γὰρ ὁ υἱὸς τοῦ ἀνθρώπου σῶσαι τὸ ἀπολωλός.[^Matthew_18_11_t]",
            "**11** "
            + RED
            + "Ἦλθεν γὰρ ὁ υἱὸς τοῦ ἀνθρώπου σῶσαι τὸ ἀπολωλός."
            + f"{END}[^Matthew_18_11_t]",
        ),
        (
            "Matthew 23:14",
            "**14** Οὐαὶ ὑμῖν, γραμματεῖς καὶ Φαρισαῖοι ὑποκριταί, ὅτι "
            "κατεσθίετε τὰς οἰκίας τῶν χηρῶν καὶ προφάσει μακρὰ προσευχόμενοι"
            + MDOT
            + " διὰ τοῦτο λήψεσθε περισσότερον κρίμα.[^Matthew_23_14_t]",
            "**14** "
            + RED
            + "Οὐαὶ ὑμῖν, γραμματεῖς καὶ Φαρισαῖοι ὑποκριταί, ὅτι "
            "κατεσθίετε τὰς οἰκίας τῶν χηρῶν καὶ προφάσει μακρὰ προσευχόμενοι"
            + MDOT
            + " διὰ τοῦτο λήψεσθε περισσότερον κρίμα."
            + f"{END}[^Matthew_23_14_t]",
        ),
        (
            "Mark 9:44",
            "**44** ὅπου ὁ σκώληξ αὐτῶν οὐ τελευτᾷ, καὶ τὸ πῦρ οὐ σβέννυται.[^Mark_9_44_t]",
            "**44** "
            + RED
            + "ὅπου ὁ σκώληξ αὐτῶν οὐ τελευτᾷ, καὶ τὸ πῦρ οὐ σβέννυται."
            + f"{END}[^Mark_9_44_t]",
        ),
        (
            "Mark 9:46",
            "**46** ὅπου ὁ σκώληξ αὐτῶν οὐ τελευτᾷ, καὶ τὸ πῦρ οὐ σβέννυται.[^Mark_9_46_t]",
            "**46** "
            + RED
            + "ὅπου ὁ σκώληξ αὐτῶν οὐ τελευτᾷ, καὶ τὸ πῦρ οὐ σβέννυται."
            + f"{END}[^Mark_9_46_t]",
        ),
    ]
    for label, old, new in edits:
        text = _replace_once(text, old, new, label)

    # The previous verse closed the quotation because this verse was absent.
    # The period stays on that sentence; the closing quote moves to the new end.
    quote_moves = [
        (
            "Matthew 17:21",
            re.compile(
                r"(ἀδυνατήσει ὑμῖν)\."
                + RD
                + r"(</span>\[\^Matthew_17_20_a\])\n+\*\*21\*\* "
                r"(Τοῦτο δὲ τὸ γένος οὐκ ἐκπορεύεται εἰ μὴ ἐν προσευχῇ καὶ νηστείᾳ)"
                r"\.(\[\^Matthew_17_21_t\])"
            ),
            r"\1.\2" + "\n\n**21** " + RED + r"\3." + RD + END + r"\4",
        ),
        (
            "Mark 7:16",
            re.compile(
                r"(τὸν ἄνθρωπον)\."
                + RD
                + r"(</span>)\n+\*\*16\*\* "
                r"(Εἴ τις ἔχει ὦτα ἀκούειν ἀκουέτω)"
                r"\.(\[\^Mark_7_16_t\])"
            ),
            r"\1.\2" + "\n\n**16** " + RED + r"\3." + RD + END + r"\4",
        ),
        (
            "Mark 11:26",
            re.compile(
                r"(τὰ παραπτώματα ὑμῶν)\."
                + RD
                + r"(</span>\[\^Mark_11_25_f\])\n+\*\*26\*\* "
                r"(Εἰ δὲ ὑμεῖς οὐκ ἀφίετε, οὐδὲ ὁ πατὴρ ὑμῶν ὁ ἐν τοῖς οὐρανοῖς "
                r"ἀφήσει τὰ παραπτώματα ὑμῶν)"
                r"\.(\[\^Mark_11_26_t\])"
            ),
            r"\1.\2" + "\n\n**26** " + RED + r"\3." + RD + END + r"\4",
        ),
        (
            "Luke 17:36",
            re.compile(
                r"(ἡ δὲ ἑτέρα ἀφεθήσεται)\."
                + RD
                + r"(</span>\[\^Luke_17_35_d\])\n+\*\*36\*\* "
                r"(δύο ἔσονται ἐν τῷ ἀγρῷ"
                + MDOT
                + r" ὁ εἷς παραληφθήσεται, καὶ ὁ ἕτερος ἀφεθήσεται)"
                r"\.(\[\^Luke_17_36_t\])"
            ),
            r"\1.\2" + "\n\n**36** " + RED + r"\3." + RD + END + r"\4",
        ),
    ]
    for label, pattern, repl in quote_moves:
        text = _sub_once(text, pattern, repl, label)

    if f"{RED} τὸ {END}" in text:
        raise RuntimeError("Luke 11:2 still has the stray article")
    misplaced = (
        (
            "Matthew 17:21",
            "### The Second Prediction of the Passion<br>"
            '*<span style="color:#0092F2">(Mark 9:30-32; Luke 9:43-45)</span>*\n\n**21**',
        ),
        (
            "Mark 11:26",
            "### Jesus' Authority Challenged<br>"
            '*<span style="color:#0092F2">(Matthew 21:23-27; Luke 20:1-8)</span>*\n\n**26**',
        ),
        (
            "Romans 16:24",
            "### Doxology<br>"
            '*<span style="color:#0092F2">(Romans 11:33-36; Jude 1:24-25)</span>*\n\n**24**',
        ),
    )
    for label, snippet in misplaced:
        if snippet in text:
            raise RuntimeError(f"{label} is still under the next heading")
    return text


def fit_restored_lines(text: str) -> str:
    """Seat each restored clause in the sentence or the poem around it.

    Poetry follows the indent already on that poem: four ``&nbsp;`` for a
    line that starts a sentence or a verse, eight for a continuation.
    A period or closing quote that belonged to the shorter reading moves
    past the words that now complete it.
    """
    indent1 = "&nbsp;" * 4
    indent2 = "&nbsp;" * 8
    edits: list[tuple[str, str, str]] = [
        (
            "Hebrews 2:7",
            f"> {indent2}δόξῃ καὶ τιμῇ ἐστεφάνωσας αὐτόν, "
            "καὶ κατέστησας αὐτὸν ἐπὶ τὰ ἔργα τῶν χειρῶν σου "
            "[^Hebrews_2_7_b]<br>",
            f"> {indent2}δόξῃ καὶ τιμῇ ἐστεφάνωσας αὐτόν,<br>\n"
            f"> {indent2}καὶ κατέστησας αὐτὸν ἐπὶ τὰ ἔργα τῶν χειρῶν σου"
            "[^Hebrews_2_7_b]<br>",
        ),
        (
            "Matthew 28:9",
            "**9** καὶ Ὡς δὲ ἐπορεύοντο ἀπαγγεῖλαι τοῖς μαθηταῖς αὐτοῦ "
            "[^Matthew_28_9_b] ἰδοὺ",
            "**9** Ὡς δὲ ἐπορεύοντο ἀπαγγεῖλαι τοῖς μαθηταῖς αὐτοῦ "
            "καὶ [^Matthew_28_9_b] ἰδοὺ",
        ),
        (
            "Mark 7:24",
            "εἰς τὰ ὅρια Τύρου. καὶ Σιδῶνος [^Mark_7_24_i] Καὶ εἰσελθὼν",
            "εἰς τὰ ὅρια Τύρου καὶ Σιδῶνος.[^Mark_7_24_i] Καὶ εἰσελθὼν",
        ),
        (
            "Mark 2:16",
            f"ἁμαρτωλῶν ἐσθίει;{RD} καὶ πίνει [^Mark_2_16_a]",
            f"ἁμαρτωλῶν ἐσθίει καὶ πίνει;{RD}[^Mark_2_16_a]",
        ),
        (
            "Luke 1:28",
            f"ὁ Κύριος μετὰ σοῦ.{RD} εὐλογημένη σὺ ἐν γυναιξίν [^Luke_1_28_a]",
            f"ὁ Κύριος μετὰ σοῦ, εὐλογημένη σὺ ἐν γυναιξίν.{RD}[^Luke_1_28_a]",
        ),
        (
            "Luke 9:54",
            f"ἀναλῶσαι αὐτούς;{RD} ὡς καὶ Ἠλίας ἐποίησεν [^Luke_9_54_b]",
            f"ἀναλῶσαι αὐτούς, ὡς καὶ Ἠλίας ἐποίησεν;{RD}[^Luke_9_54_b]",
        ),
        (
            "Luke 20:30",
            "**30** καὶ ὁ δεύτερος καὶ ἔλαβεν ὁ δεύτερος τὴν γυναῖκα, "
            "καὶ οὗτος ἀπέθανεν ἄτεκνος [^Luke_20_30_c]",
            "**30** καὶ ἔλαβεν ὁ δεύτερος τὴν γυναῖκα, "
            "καὶ οὗτος ἀπέθανεν ἄτεκνος.[^Luke_20_30_c]",
        ),
        (
            "Luke 23:23",
            "αἱ φωναὶ αὐτῶν. καὶ τῶν ἀρχιερέων [^Luke_23_23_b]",
            "αἱ φωναὶ αὐτῶν καὶ τῶν ἀρχιερέων.[^Luke_23_23_b]",
        ),
        (
            "Luke 24:42",
            f"ἰχθύος καὶ ἀπὸ μελισσίου κηρίου [^Luke_24_42_b] ὀπτοῦ μέρος{MDOT}",
            f"ἰχθύος ὀπτοῦ μέρος καὶ ἀπὸ μελισσίου κηρίου{MDOT}[^Luke_24_42_b]",
        ),
        (
            "Acts 18:21",
            "καὶ εἰπών Δεῖ με πάντως τὴν ἑορτὴν τὴν ἐρχομένην ποιῆσαι "
            f"εἰς Ἱεροσόλυμα{MDOT} πάλιν δὲ [^Acts_18_21_a] {LD}Πάλιν "
            f"ἀνακάμψω πρὸς ὑμᾶς τοῦ Θεοῦ θέλοντος,{RD}",
            f"καὶ εἰπών {LD}Δεῖ με πάντως τὴν ἑορτὴν τὴν ἐρχομένην ποιῆσαι "
            f"εἰς Ἱεροσόλυμα{MDOT} πάλιν δὲ ἀνακάμψω πρὸς ὑμᾶς τοῦ Θεοῦ "
            f"θέλοντος,{RD}[^Acts_18_21_a]",
        ),
        (
            "Acts 8:37",
            "εἶπε δὲ ὁ Φίλιππος, Εἰ πιστεύεις ἐξ ὅλης τῆς καρδίας, ἔξεστιν. "
            "ἀποκριθεὶς δὲ εἶπε, Πιστεύω τὸν υἱὸν τοῦ Θεοῦ εἶναι τὸν "
            "Ἰησοῦν Χριστόν.[^Acts_8_37_t]",
            "εἶπε δὲ ὁ Φίλιππος, "
            + LD
            + "Εἰ πιστεύεις ἐξ ὅλης τῆς καρδίας, ἔξεστιν."
            + RD
            + " ἀποκριθεὶς δὲ εἶπε, "
            + LD
            + "Πιστεύω τὸν υἱὸν τοῦ Θεοῦ εἶναι τὸν Ἰησοῦν Χριστόν."
            + RD
            + "[^Acts_8_37_t]",
        ),
        (
            "Romans 8:1",
            "τοῖς ἐν Χριστῷ Ἰησοῦ. μὴ κατὰ σάρκα περιπατοῦσιν, "
            "ἀλλὰ κατὰ πνεῦμα. [^Romans_8_1_a]",
            "τοῖς ἐν Χριστῷ Ἰησοῦ μὴ κατὰ σάρκα περιπατοῦσιν, "
            "ἀλλὰ κατὰ πνεῦμα.[^Romans_8_1_a]",
        ),
        (
            "Romans 14:21",
            "ὁ ἀδελφός σου προσκόπτει. ἢ σκανδαλίζεται ἢ ἀσθενεῖ "
            "[^Romans_14_21_d]",
            "ὁ ἀδελφός σου προσκόπτει ἢ σκανδαλίζεται ἢ ἀσθενεῖ."
            "[^Romans_14_21_d]",
        ),
        (
            "Ephesians 5:30",
            "τοῦ σώματος αὐτοῦ. ἐκ τῆς σαρκὸς αὐτοῦ καὶ ἐκ τῶν ὀστέων αὐτοῦ "
            "[^Ephesians_5_30_a]",
            "τοῦ σώματος αὐτοῦ, ἐκ τῆς σαρκὸς αὐτοῦ καὶ ἐκ τῶν ὀστέων αὐτοῦ."
            "[^Ephesians_5_30_a]",
        ),
        (
            "Hebrews 3:6",
            "καὶ τὸ καύχημα τῆς ἐλπίδος κατάσχωμεν. μέχρι τέλους βεβαίαν "
            "[^Hebrews_3_6_b]",
            "καὶ τὸ καύχημα τῆς ἐλπίδος μέχρι τέλους βεβαίαν κατάσχωμεν."
            "[^Hebrews_3_6_b]",
        ),
        (
            "1 Thessalonians 1:1",
            "Χάρις ὑμῖν καὶ εἰρήνη. ἀπὸ Θεοῦ πατρὸς ἡμῶν, καὶ κυρίου "
            "Ἰησοῦ Χριστοῦ [^1_Thessalonians_1_1_b]",
            "Χάρις ὑμῖν καὶ εἰρήνη ἀπὸ Θεοῦ Πατρὸς ἡμῶν καὶ Κυρίου "
            "Ἰησοῦ Χριστοῦ.[^1_Thessalonians_1_1_b]",
        ),
        (
            "1 Peter 4:14",
            f"ἐφ{RQ} ὑμᾶς ἀναπαύεται. κατὰ μὲν αὐτοὺς βλασφημεῖται, "
            "κατὰ δὲ ὑμᾶς δοξάζεται. [^1_Peter_4_14_b]",
            f"ἐφ{RQ} ὑμᾶς ἀναπαύεται{MDOT} κατὰ μὲν αὐτοὺς βλασφημεῖται, "
            "κατὰ δὲ ὑμᾶς δοξάζεται.[^1_Peter_4_14_b]",
        ),
        (
            "Revelation 14:5",
            "ἄμωμοί εἰσιν. ἐνώπιον τοῦ θρόνου τοῦ Θεοῦ [^Revelation_14_5_a]",
            "ἄμωμοί εἰσιν ἐνώπιον τοῦ θρόνου τοῦ Θεοῦ.[^Revelation_14_5_a]",
        ),
        (
            "Ephesians 3:14",
            "πρὸς τὸν Πατέρα, τοῦ κυρίου ἡμῶν Ἰησοῦ χριστοῦ "
            "[^Ephesians_3_14_a]",
            "πρὸς τὸν Πατέρα τοῦ Κυρίου ἡμῶν Ἰησοῦ Χριστοῦ,"
            "[^Ephesians_3_14_a]",
        ),
        (
            "1 John 5:13",
            "καὶ ἵνα πιστεύητε εἰς τὸ ὄνομα τοῦ υἱοῦ τοῦ θεοῦ,",
            "καὶ ἵνα πιστεύητε εἰς τὸ ὄνομα τοῦ Υἱοῦ τοῦ Θεοῦ,",
        ),
    ]
    for label, old, new in edits:
        text = _replace_once(text, old, new, label)
    if f"> {indent1}{RED}Ὅτι σοῦ ἐστιν ἡ βασιλεία" not in text:
        raise RuntimeError("Matthew 6:13 doxology was not given its own line")
    if f"{RED} τὸ {END}" in text:
        raise RuntimeError("Luke 11:2 still has the stray article")
    return text


def ensure_luke_9_56_see_note(text: str) -> str:
    """The second colon is in verse 56. The attestation stays on verse 55."""
    key = "Luke_9_56_t"
    line = f"[^{key}]: See note on v. 55."
    existing = re.compile(rf"^\[\^{key}\]:.*$", re.M)
    if existing.search(text):
        return existing.sub(line, text, count=1)
    anchor = re.compile(r"^(\[\^Luke_9_55_c\]:.*)$", re.M)
    found = anchor.search(text)
    if not found:
        raise RuntimeError("Luke 9:55 note is missing")
    return text[: found.end()] + "\n" + line + text[found.end() :]


def apply(md: str) -> str:
    md = number_three_john(md)
    md = number_revelation_sand(md)
    if md.count(COMMA_OLD) != 1:
        raise RuntimeError("1 John 5:7–8: expected the short reading once")
    md = md.replace(COMMA_OLD, COMMA_NEW, 1)
    if len(COMMA_NOTE_RE.findall(md)) != 1:
        raise RuntimeError("1 John 5:7–8: expected one attestation note")
    md = COMMA_NOTE_RE.sub(COMMA_NOTE, md, count=1)
    md = cover_noted_clauses(md)
    md = reword_body_includes(md)
    md = tidy_note_definitions(md)
    md = redden_jesus_restorations(md)
    md = fit_restored_lines(md)
    return ensure_luke_9_56_see_note(md)
