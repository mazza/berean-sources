# Berean sources

Hebrew, Aramaic, and Greek Scripture drawn from Berean Bible materials, as chapter Markdown. This is **not** an official repository of Berean Bible or Bible Hub. They dedicated the texts to the public domain (CC0) on 30 April 2023 so that other people could use them. The repository is named `berean-sources` because the Old Testament, the New Testament, and the morphology table come from different files on their site. It is not the Berean Standard Bible, the Berean Literal Bible, the Berean Study Bible, the Berean Greek Bible, or the Berean Interlinear Bible.

The text here is the original-language layer those English Bibles are built from, plus the classic verses the critical base does not print. Because of that addition it is not a verbatim copy of one of their editions. Berean ask that works which vary from their official text not use the Berean name. The name of this repository only identifies the CC0 source.

| Piece | Where |
|---|---|
| Upstream | [Berean Bible downloads](https://berean.bible/downloads.htm), CC0 |
| Terms | [berean.bible/terms.htm](https://berean.bible/terms.htm) |
| Downloads the pipeline reads | `archive/bsb_tables.tsv`, `archive/bgb.docx` |
| Chapters | [CANON.md](CANON.md) |
| Notice and titles | [`front/`](front/) |
| Morphology, original-language order | [`extra/tables-original-order.tsv`](extra/tables-original-order.tsv) |
| Checks | [`QUALITY.md`](QUALITY.md) |
| Greek notation | [`docs/notation.md`](docs/notation.md) |
| Inventory | [`manifest.json`](manifest.json) |

## Path

```text
https://berean.bible/downloads/bsb_tables.tsv
  → pipeline/fetch_archive.py
  → archive/bsb_tables.tsv
       → pipeline/hebrew_tsv_to_markdown.py → prepared/hebrew-ot.md
       → pipeline/reorder_tables.py         → extra/tables-original-order.tsv

https://berean.bible/downloads/bgb.docx
  → pipeline/fetch_archive.py
  → archive/bgb.docx
       → pipeline/prepare_greek_docx.py      → prepared/_work/bgb-edited.docx
       → pipeline/greek_docx_to_markdown.py  → prepared/greek-nt.md
         (pipeline/errata.tsv, pipeline/critical_verses.tsv;
          the script calls apply_berean_errata, apply_verse_completeness,
          and apply_protestant_coverage — they are not separate steps)

prepared/hebrew-ot.md + prepared/greek-nt.md
  → pipeline/build_canon.py → canon/NN-BBB/CC.md
```

`archive/` keeps the downloads unchanged. `prepared/` is the continuous text. `canon/` is the chapter result. `prepared/_work/` is not stored in Git. The Greek steps need `python-docx`. `fetch_archive.py` downloads again only when the sha256 does not match the manifest.

## Rebuild

```bash
python3 pipeline/fetch_archive.py
python3 pipeline/hebrew_tsv_to_markdown.py
python3 pipeline/reorder_tables.py
python3 pipeline/prepare_greek_docx.py
python3 pipeline/greek_docx_to_markdown.py
python3 pipeline/build_canon.py
python3 pipeline/verify.py
```

That reproduces `prepared/`, `extra/tables-original-order.tsv`, and `canon/` from the downloads, then checks the result.

## Joined Markdown

```bash
python3 pipeline/build_bible.py [--original] [--testament ot|nt] [--output PATH]
```

`build_bible.py` reads the chapters in `canon/` and writes one Markdown file. `--testament ot` keeps the Hebrew and Aramaic books (folders 01-39). `--testament nt` keeps the Greek books (folders 41-67). Omit it for both. Without `--original` the book titles are the ordinary English names (`# Psalms`). With `--original`, the provenance notice comes first and the book titles are the ones Berean prints (`# Psalm`). The output goes to `dist/`, which is not stored in Git. The file name gains `-original`, `-ot`, and `-nt` to match the options. `--output` replaces that path and keeps the same selection.

The morphology table in `extra/` stays a separate file. Its scope is both testaments, in one original-language order, so `--testament` does not split it. See [`docs/format.md`](docs/format.md).

## Restored verses

The Greek follows the Berean Greek Bible. Its base is Nestle 1904. Verses widely printed in the Byzantine text and the Textus Receptus, and absent from that base, are printed in the chapter with a footnote. The published id uses the chapter's letter order (`a`, `b`, … `z`, `aa`), not a private final letter. The restored list is [`pipeline/critical_verses.tsv`](pipeline/critical_verses.tsv): those sixteen verses are in the body, each with a note. The words are not in brackets. A Berean note that records a Byzantine or Textus Receptus clause is also placed in that verse, so a Protestant edition is not missing its wording.

3 John 15 and Revelation 12:18 are a separate renumbering, not rows on that list. The sentences were already in the Berean download; `apply_protestant_coverage.py` gives them the Protestant verse numbers. 1 John 5:7–8 includes the heavenly witnesses in the wording of Scrivener 1894, with an attestation note.

## License

The Berean source text and this structuring are [CC0 1.0](LICENSE). The verse-maximum table used by the check is Copenhagen `eng.json`, which is CC BY-SA 4.0. It is a count of verses, not the wording. See [`NOTICE.md`](NOTICE.md).
