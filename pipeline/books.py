"""Protestant book identity for the Berean original-language text.

``chapter_name`` is the heading Berean uses (``## Psalm 1``).
``modern_name`` is the English book name in the reading index.
They differ only for Psalms.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    folder: str
    usfm: str
    chapter_name: str
    modern_name: str
    slug: str
    lang: str

    @property
    def order(self) -> int:
        return int(self.folder.split("-", 1)[0])


def _b(folder, usfm, name, slug, lang, modern=None):
    return Book(folder, usfm, name, modern or name, slug, lang)


BOOKS: tuple[Book, ...] = (
    _b("01-GEN", "GEN", "Genesis", "Genesis", "hbo"),
    _b("02-EXO", "EXO", "Exodus", "Exodus", "hbo"),
    _b("03-LEV", "LEV", "Leviticus", "Leviticus", "hbo"),
    _b("04-NUM", "NUM", "Numbers", "Numbers", "hbo"),
    _b("05-DEU", "DEU", "Deuteronomy", "Deuteronomy", "hbo"),
    _b("06-JOS", "JOS", "Joshua", "Joshua", "hbo"),
    _b("07-JDG", "JDG", "Judges", "Judges", "hbo"),
    _b("08-RUT", "RUT", "Ruth", "Ruth", "hbo"),
    _b("09-1SA", "1SA", "1 Samuel", "1_Samuel", "hbo"),
    _b("10-2SA", "2SA", "2 Samuel", "2_Samuel", "hbo"),
    _b("11-1KI", "1KI", "1 Kings", "1_Kings", "hbo"),
    _b("12-2KI", "2KI", "2 Kings", "2_Kings", "hbo"),
    _b("13-1CH", "1CH", "1 Chronicles", "1_Chronicles", "hbo"),
    _b("14-2CH", "2CH", "2 Chronicles", "2_Chronicles", "hbo"),
    _b("15-EZR", "EZR", "Ezra", "Ezra", "hbo"),
    _b("16-NEH", "NEH", "Nehemiah", "Nehemiah", "hbo"),
    _b("17-EST", "EST", "Esther", "Esther", "hbo"),
    _b("18-JOB", "JOB", "Job", "Job", "hbo"),
    _b("19-PSA", "PSA", "Psalm", "Psalm", "hbo", modern="Psalms"),
    _b("20-PRO", "PRO", "Proverbs", "Proverbs", "hbo"),
    _b("21-ECC", "ECC", "Ecclesiastes", "Ecclesiastes", "hbo"),
    _b("22-SNG", "SNG", "Song of Solomon", "Song_of_Solomon", "hbo"),
    _b("23-ISA", "ISA", "Isaiah", "Isaiah", "hbo"),
    _b("24-JER", "JER", "Jeremiah", "Jeremiah", "hbo"),
    _b("25-LAM", "LAM", "Lamentations", "Lamentations", "hbo"),
    _b("26-EZK", "EZK", "Ezekiel", "Ezekiel", "hbo"),
    _b("27-DAN", "DAN", "Daniel", "Daniel", "hbo"),
    _b("28-HOS", "HOS", "Hosea", "Hosea", "hbo"),
    _b("29-JOL", "JOL", "Joel", "Joel", "hbo"),
    _b("30-AMO", "AMO", "Amos", "Amos", "hbo"),
    _b("31-OBA", "OBA", "Obadiah", "Obadiah", "hbo"),
    _b("32-JON", "JON", "Jonah", "Jonah", "hbo"),
    _b("33-MIC", "MIC", "Micah", "Micah", "hbo"),
    _b("34-NAM", "NAM", "Nahum", "Nahum", "hbo"),
    _b("35-HAB", "HAB", "Habakkuk", "Habakkuk", "hbo"),
    _b("36-ZEP", "ZEP", "Zephaniah", "Zephaniah", "hbo"),
    _b("37-HAG", "HAG", "Haggai", "Haggai", "hbo"),
    _b("38-ZEC", "ZEC", "Zechariah", "Zechariah", "hbo"),
    _b("39-MAL", "MAL", "Malachi", "Malachi", "hbo"),
    _b("41-MAT", "MAT", "Matthew", "Matthew", "grc"),
    _b("42-MRK", "MRK", "Mark", "Mark", "grc"),
    _b("43-LUK", "LUK", "Luke", "Luke", "grc"),
    _b("44-JHN", "JHN", "John", "John", "grc"),
    _b("45-ACT", "ACT", "Acts", "Acts", "grc"),
    _b("46-ROM", "ROM", "Romans", "Romans", "grc"),
    _b("47-1CO", "1CO", "1 Corinthians", "1_Corinthians", "grc"),
    _b("48-2CO", "2CO", "2 Corinthians", "2_Corinthians", "grc"),
    _b("49-GAL", "GAL", "Galatians", "Galatians", "grc"),
    _b("50-EPH", "EPH", "Ephesians", "Ephesians", "grc"),
    _b("51-PHP", "PHP", "Philippians", "Philippians", "grc"),
    _b("52-COL", "COL", "Colossians", "Colossians", "grc"),
    _b("53-1TH", "1TH", "1 Thessalonians", "1_Thessalonians", "grc"),
    _b("54-2TH", "2TH", "2 Thessalonians", "2_Thessalonians", "grc"),
    _b("55-1TI", "1TI", "1 Timothy", "1_Timothy", "grc"),
    _b("56-2TI", "2TI", "2 Timothy", "2_Timothy", "grc"),
    _b("57-TIT", "TIT", "Titus", "Titus", "grc"),
    _b("58-PHM", "PHM", "Philemon", "Philemon", "grc"),
    _b("59-HEB", "HEB", "Hebrews", "Hebrews", "grc"),
    _b("60-JAS", "JAS", "James", "James", "grc"),
    _b("61-1PE", "1PE", "1 Peter", "1_Peter", "grc"),
    _b("62-2PE", "2PE", "2 Peter", "2_Peter", "grc"),
    _b("63-1JN", "1JN", "1 John", "1_John", "grc"),
    _b("64-2JN", "2JN", "2 John", "2_John", "grc"),
    _b("65-3JN", "3JN", "3 John", "3_John", "grc"),
    _b("66-JUD", "JUD", "Jude", "Jude", "grc"),
    _b("67-REV", "REV", "Revelation", "Revelation", "grc"),
)

BY_SLUG = {b.slug: b for b in BOOKS}
BY_CHAPTER_NAME = {b.chapter_name: b for b in BOOKS}


def books_for(testament: str | None) -> tuple[Book, ...]:
    """Books for one export.

    ``ot`` is folders 01-39, ``nt`` is folders 41-67, and ``None`` is every
    book in ``BOOKS``. Folder 40 is not used.
    """
    if testament is None:
        return BOOKS
    if testament == "ot":
        return tuple(book for book in BOOKS if book.order < 40)
    if testament == "nt":
        return tuple(book for book in BOOKS if book.order > 40)
    raise ValueError(f"unknown testament {testament!r}")


def chapter_filename(folder: str, number: int) -> str:
    """Psalm files are ``001.md``–``150.md``. Every other book stays at two digits."""
    width = 3 if folder == "19-PSA" else 2
    return f"{number:0{width}d}.md"


def note_letter(index: int) -> str:
    """Letter of the note at ``index`` in its chapter.

    ``0`` is ``a``, ``25`` is ``z``, ``26`` is ``aa``, ``27`` is ``ab``.
    Inserting a note shifts every later note in that chapter.
    """
    n = index + 1
    chars: list[str] = []
    while n:
        n, rem = divmod(n - 1, 26)
        chars.append(chr(ord("a") + rem))
    return "".join(reversed(chars))
