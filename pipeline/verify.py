#!/usr/bin/env python3
"""Check the Berean chapter files.

Verse maxima from Copenhagen eng.json are compared and printed. A mismatch
is not a failure where Berean versification differs from the English count.
3 John is expected to end at 15 and Revelation 12 at 18: those numbers come
from apply_protestant_coverage.py, not from a missing row in
critical_verses.tsv. Disorder, a missing restored verse, or a broken
footnote is a failure.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from books import BOOKS, chapter_filename, note_letter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "canon"
LIMITS = Path(__file__).resolve().parent / "verse_limits.tsv"
CRITICAL = Path(__file__).resolve().parent / "critical_verses.tsv"
HEADER_RE = re.compile(
    r"<!--\nedition: berean\nbook: ([0-9]{2}-[0-9A-Z]{3})\nchapter: (\d+)\nlang: (hbo|grc)\n-->"
)
VERSE_RE = re.compile(r"\*\*(\d+)\*\*")
FN_RE = re.compile(r"\[\^([0-9A-Z]+_\d+_\d+_[a-z]+)\]")
DEF_RE = re.compile(r"^\[\^([0-9A-Z]+_\d+_\d+_[a-z]+)\]: ")
ID_PARTS = re.compile(r"^([0-9A-Z]+)_(\d+)_(\d+)_([a-z]+)$")


def load_limits() -> dict[tuple[str, int], int]:
    limits: dict[tuple[str, int], int] = {}
    for line in LIMITS.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("book"):
            continue
        folder, chapter, maximum = line.split("\t")
        limits[(folder, int(chapter))] = int(maximum)
    return limits


EXTRA_ID_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
SCOPES = {"ot", "nt", "ot-nt"}


def reading_present(text: str, greek: str) -> bool:
    """The restored words are in the chapter.

    Quotation marks may wrap speech without changing those words.
    """
    if greek in text:
        return True
    drop = str.maketrans("", "", "“”‘’")
    return greek.translate(drop) in text.translate(drop)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_extras(errors: list[str]) -> int:
    """Declared extras must match extra/. Return how many the manifest lists."""
    try:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"manifest.json: {exc}")
        return 0
    extras = manifest.get("extras")
    if not isinstance(extras, list):
        errors.append("manifest.json: extras must be a list")
        return 0
    declared: set[str] = set()
    seen_ids: set[str] = set()
    for index, item in enumerate(extras):
        where = f"manifest.json extras[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: must be an object")
            continue
        ident = item.get("id")
        if not isinstance(ident, str) or EXTRA_ID_RE.fullmatch(ident) is None:
            errors.append(f"{where}: id must be kebab-case")
        elif ident in seen_ids:
            errors.append(f"{where}: duplicate id {ident}")
        else:
            seen_ids.add(ident)
        role = item.get("role")
        if not isinstance(role, str) or EXTRA_ID_RE.fullmatch(role) is None:
            errors.append(f"{where}: role must be kebab-case")
        media = item.get("media_type")
        if (
            not isinstance(media, str)
            or media.count("/") != 1
            or " " in media
            or any(part == "" for part in media.split("/"))
        ):
            errors.append(f"{where}: media_type must be a type/subtype")
        if item.get("scope") not in SCOPES:
            errors.append(f"{where}: scope must be ot, nt, or ot-nt")
        description = item.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append(f"{where}: description is required")
        digest = item.get("sha256")
        if not isinstance(digest, str) or SHA_RE.fullmatch(digest) is None:
            errors.append(f"{where}: sha256 must be 64 lowercase hex characters")
            digest = None
        size = item.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            errors.append(f"{where}: bytes must be a non-negative integer")
            size = None
        path_text = item.get("path")
        if (
            not isinstance(path_text, str)
            or path_text == "extra/README.md"
            or not path_text.startswith("extra/")
            or path_text.endswith("/")
            or any(part in {"", ".", ".."} for part in path_text.split("/"))
        ):
            errors.append(f"{where}: path must be a file under extra/")
            continue
        if path_text in declared:
            errors.append(f"{where}: duplicate path {path_text}")
            continue
        declared.add(path_text)
        path = ROOT / path_text
        if not path.is_file():
            errors.append(f"{path_text}: missing")
            continue
        actual_size = path.stat().st_size
        if size is not None and actual_size != size:
            errors.append(f"{path_text}: bytes {actual_size}, manifest {size}")
        if digest is not None and sha256_file(path) != digest:
            errors.append(f"{path_text}: sha256 does not match")
    extra_dir = ROOT / "extra"
    if not extras:
        if extra_dir.exists():
            errors.append("extra/ exists but extras is empty")
        return 0
    if not (extra_dir / "README.md").is_file():
        errors.append("extra/README.md missing")
    if extra_dir.exists() and not extra_dir.is_dir():
        errors.append("extra must be a directory")
        return len(extras)
    if extra_dir.is_dir():
        for file in sorted(path for path in extra_dir.rglob("*") if path.is_file()):
            rel = file.relative_to(ROOT).as_posix()
            if rel == "extra/README.md":
                continue
            if rel not in declared:
                errors.append(f"{rel}: not listed in manifest extras")
    return len(extras)


def check_stage(errors: list[str], key: str) -> None:
    """Pinned archive or prepared files must match the manifest hash and size."""
    try:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"manifest.json: {exc}")
        return
    items = manifest.get(key)
    if not isinstance(items, list):
        errors.append(f"manifest.json: {key} must be a list")
        return
    for index, item in enumerate(items):
        where = f"manifest.json {key}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: must be an object")
            continue
        path_text = item.get("path")
        if (
            not isinstance(path_text, str)
            or path_text.startswith("/")
            or any(part in {"", ".", ".."} for part in path_text.split("/"))
        ):
            errors.append(f"{where}: path is required")
            continue
        path = ROOT / path_text
        if not path.is_file():
            errors.append(f"{path_text}: missing")
            continue
        digest = item.get("sha256")
        if not isinstance(digest, str) or SHA_RE.fullmatch(digest) is None:
            errors.append(f"{where}: sha256 must be 64 lowercase hex characters")
        elif sha256_file(path) != digest:
            errors.append(f"{path_text}: sha256 does not match")
        size = item.get("bytes")
        actual = path.stat().st_size
        if isinstance(size, bool) or not isinstance(size, int) or actual != size:
            errors.append(f"{path_text}: bytes {actual}, manifest {size}")


def main() -> int:
    errors: list[str] = []
    check_stage(errors, "archive")
    check_stage(errors, "prepared")
    extra_count = check_extras(errors)
    limits = load_limits()
    index = (ROOT / "CANON.md").read_text(encoding="utf-8")
    titles = (ROOT / "front" / "titles.md").read_text(encoding="utf-8")
    ids: dict[str, str] = {}
    files = 0
    verses = 0
    limit_diff = 0
    for book in BOOKS:
        if f"## {book.folder}\n" not in titles:
            errors.append(f"front/titles.md missing {book.folder}")
        folder = CANON / book.folder
        found = sorted(folder.glob("*.md"), key=lambda path: int(path.stem))
        for path in found:
            files += 1
            text = path.read_text(encoding="utf-8")
            if "\ufffd" in text:
                errors.append(f"{path}: replacement character")
            header = HEADER_RE.match(text)
            if not header:
                errors.append(f"{path}: bad header")
                continue
            if header.group(1) != book.folder or header.group(3) != book.lang:
                errors.append(f"{path}: header does not match the book")
            if chapter_filename(book.folder, int(header.group(2))) != path.name:
                errors.append(f"{path}: chapter does not match the file name")
            if re.search(r"(?m)^# ", text):
                errors.append(f"{path}: book title belongs in front/titles.md")
            numbers = [int(n) for n in VERSE_RE.findall(text)]
            if not numbers:
                errors.append(f"{path}: no verses")
            elif any(b <= a for a, b in zip(numbers, numbers[1:])):
                errors.append(f"{path}: verse numbers do not increase")
            verses += len(numbers)
            chapter = int(path.stem)
            maximum = limits.get((book.folder, chapter))
            if maximum is not None and (not numbers or numbers[-1] != maximum or len(numbers) != maximum):
                limit_diff += 1
            if f"](canon/{book.folder}/{path.name})" not in index:
                errors.append(f"{path}: missing from CANON.md")
            markers: list[str] = []
            defs: list[str] = []
            for line in text.splitlines():
                if DEF_RE.match(line):
                    defs.append(DEF_RE.match(line).group(1))
                else:
                    markers.extend(FN_RE.findall(line))
            ordered: list[str] = []
            for ident in markers:
                if ident not in ordered:
                    ordered.append(ident)
            if ordered != defs:
                errors.append(f"{path}: {len(ordered)} notes, {len(defs)} definitions")
            verse_set = set(numbers)
            chapter_number = int(header.group(2))
            for note_index, ident in enumerate(ordered):
                parsed = ID_PARTS.match(ident)
                expect = note_letter(note_index)
                if (
                    not parsed
                    or parsed.group(1) != book.usfm
                    or int(parsed.group(2)) != chapter_number
                    or parsed.group(4) != expect
                    or int(parsed.group(3)) not in verse_set
                ):
                    errors.append(
                        f"{path}: note {ident} is not "
                        f"{book.usfm}_{chapter_number}_<verse>_{expect}"
                    )
            for ident in defs:
                if ident in ids:
                    errors.append(f"duplicate id {ident}")
                ids[ident] = str(path.relative_to(ROOT))
    for line in CRITICAL.read_text(encoding="utf-8").splitlines()[1:]:
        if not line.strip():
            continue
        book_name, chapter, verse, greek, _note, _source = line.split("\t")
        book = next(item for item in BOOKS if item.chapter_name == book_name)
        path = CANON / book.folder / chapter_filename(book.folder, int(chapter))
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        if f"**{verse}**" not in text or not reading_present(text, greek):
            errors.append(f"restored verse missing: {book_name} {chapter}:{verse}")
    print(
        f"files {files}  verses {verses}  footnotes {len(ids)}  "
        f"eng-max differences {limit_diff}  extras {extra_count}"
    )
    for item in errors[:30]:
        print(f"error: {item}", file=sys.stderr)
    if len(errors) > 30:
        print(f"... {len(errors) - 30} more", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
