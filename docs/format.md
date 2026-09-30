# edition-canon/1

The same chapter layout as the other edition repositories. The wording is the
Berean original-language text. Identifiers do not depend on the language of
the heading. Fields this edition does not use stay in the grammar so a file
from another edition is still the same shape.

## Tree

```text
manifest.json     URLs, sha256, extras, pipeline order
archive/          upstream downloads, unchanged
prepared/         continuous Markdown built from archive/
front/            provenance notice and Berean book titles
extra/            files that are not the reading text
pipeline/         scripts from the URL bytes to canon/ and dist/
canon/NN-BBB/CC.md
CANON.md          reading index, generated
```

The pipeline starts at the download URL. `fetch_archive.py` stores those bytes in `archive/` and does not edit them. The Hebrew and Aramaic continuous text is built from `archive/bsb_tables.tsv`. The Greek continuous text is built from `archive/bgb.docx`. `build_canon.py` reads `prepared/`, not `archive/`. `prepared/_work/` is scratch and is not stored in Git.

`NN` is the Protestant order, two digits, skipping 40. `BBB` is the USFM
book code. `CC` is the chapter, two digits (`01.md`). Psalms (`19-PSA`)
uses three digits (`001.md` through `150.md`) because that book has 150
chapters. Nothing in `canon/` is edited by hand.

## Path

```text
URL in manifest.json
  → pipeline/fetch_archive.py
  → archive/
  → pipeline/hebrew_tsv_to_markdown.py
    pipeline/reorder_tables.py
    pipeline/prepare_greek_docx.py
    pipeline/greek_docx_to_markdown.py
  → prepared/
  → pipeline/build_canon.py
  → canon/
  → pipeline/build_bible.py [--original] [--testament ot|nt] [--output PATH]
  → dist/
```

`prepared/` is the continuous Markdown between the download and the chapters. An edition that does not need that step publishes `"prepared": []` and skips it. `extra/` is not on this path: `build_bible.py` does not read it, and `--testament` does not split a file whose `scope` is `ot-nt`.

## Chapter file

```markdown
<!--
edition: berean
book: 01-GEN
chapter: 1
lang: hbo
-->

## Genesis 1

### The Creation

#### (John 1:1–5; Hebrews 11:1–3)

**1** Verse text with a note[^GEN_1_3_a].

[^GEN_1_3_a]: Note text.
```

| Piece | Rule |
|---|---|
| Comment | `edition`, `book`, `chapter`, `lang`. This edition uses `hbo` or `grc`. `text` is optional and is omitted here; an edition whose verse body is still OCR writes `text: ocr`. |
| `#` | Not in the chapter. Berean's English book title is in `front/titles.md`. |
| `##` | Berean's chapter heading: `Genesis 1`, `Psalm 23`, `1 Samuel 1`. |
| `###` | Section title. A Berean song heading that is already level 4 stays `####`. |
| `#### (…)` | Parallel reference Berean prints under that heading, kept in parentheses: `#### (John 1:1–5; Hebrews 11:1–3)`. |
| Verse | `**N**`. Poetry and the red words of Jesus stay as Berean marked them. |
| Note | `[^USFM_chapter_verse_letter]`. See below. |

## Note identifier

```text
[^<USFM>_<chapter>_<verse>_<letter>]
```

Example: `[^GEN_1_1_a]`, `[^1SA_20_42_b]`, `[^MAT_17_21_b]`.

- The USFM code is the book code from the folder, without the order prefix (`MAT`, not `41-MAT`, and not the English name `Matthew`).
- Chapter and verse have no leading zeros. The verse is the first verse the note refers to. A call printed on a section heading uses the first verse of that section.
- The letter is the note's place in that chapter, in English alphabetical order: the first note is `a`, then `b`. After `z` comes `aa`, then `ab`. A note inserted earlier in the chapter shifts every later letter. The letter is not the source's own label, and it does not restart at each verse.
- The id is unique across the Bible. Joining every chapter into one Markdown file does not repeat anchors.

Greek word-order and compound-word marks from the Berean Greek Bible are notes of this shape. The brackets that stay in the line, and the two sentences the notes use, are in [`notation.md`](notation.md).

## Extra files

`extra/` holds material published with the edition that is not the reading text. `build_bible.py` does not read it. Each file is an object in the `extras` array of `manifest.json`:

| Field | Meaning |
|---|---|
| `id` | Unique kebab-case token. |
| `path` | A file under `extra/`. `extra/README.md` is the note for people and is not an entry. |
| `role` | Kebab-case token. `morphology` is a word-level table. |
| `media_type` | A type and subtype, such as `text/tab-separated-values`. |
| `scope` | `ot` for folders 01-39, `nt` for folders 41-67, or `ot-nt` when one file covers both. |
| `description` | What the file is. |
| `sha256` | Hash of the file bytes. |
| `bytes` | Size in bytes. |

`pipeline/verify.py` checks that the list and the directory agree, including the hash. An edition with nothing in this slot publishes `"extras": []` and does not create `extra/`. When `extras` has entries, `extra/README.md` is required.

`extra/tables-original-order.tsv` is the Berean morphology table reordered by Heb Sort, then Greek Sort, then BSB Sort. The header row is Berean's. The Berean download `bsb_tables.tsv` stays out of this repository. The table's scope is `ot-nt`: one original-language order, Hebrew and Aramaic followed by Greek. `--testament` selects chapters and leaves this file whole.

## Joined Markdown

`build_bible.py` joins `canon/` into one Markdown file. It reads `front/` when `--original` is set.

```bash
python3 pipeline/build_bible.py [--original] [--testament ot|nt] [--output PATH]
```

Omit `--testament` for both testaments. `ot` keeps folders 01-39. `nt` keeps folders 41-67. Chapter headings stay as Berean prints them (`## Psalm 1`). Without `--original` the book title is the ordinary English name (`# Psalms`). With `--original` the provenance notice comes first and the book title is the one Berean prints (`# Psalm`). The notice is included for a single testament as well, because that file still has to say where the slice came from.

Default paths are under `dist/`, which is not stored in Git:

| Options | File |
|---|---|
| *(none)* | `bible.md` |
| `--original` | `bible-original.md` |
| `--testament ot` | `bible-ot.md` |
| `--testament nt` | `bible-nt.md` |
| `--original --testament ot` | `bible-original-ot.md` |
| `--original --testament nt` | `bible-original-nt.md` |

`--output` replaces the path. The selection of books stays the same. The stem here is `bible`. The suffixes `-original`, `-ot`, and `-nt` are the same in every edition repository. A Portuguese edition uses the stem `biblia`.
