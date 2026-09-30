# Quality

Checked with `python3 pipeline/verify.py` after `pipeline/build_canon.py`.

| Check | Result |
|---|---|
| 66 books, 1 189 chapters | pass |
| Verse numbers increase in every chapter | pass |
| 31 104 verse markers | pass |
| 4 437 footnotes, each marker defined once in its chapter, ids unique | pass |
| No book title inside `canon/` | pass |
| `CANON.md` links every chapter file | pass |
| `front/titles.md` has all 66 books | pass |
| All 16 restored verses in `pipeline/critical_verses.tsv` are in the Greek text | pass |
| No U+FFFD | pass |
| `extra/tables-original-order.tsv` matches the sha256 and size in `manifest.json` | pass |

The Greek text is taken from `archive/bgb.docx` and the Hebrew from `archive/bsb_tables.tsv`. The scripts write `prepared/`. The chapter split changes markup and footnote ids. Word-order and compound-word marks from the Berean Greek Bible are footnotes; the reading line keeps one order and one spelling (`docs/notation.md`). `pipeline/errata.tsv` corrects a few Greek spellings, and the coverage scripts supply the Protestant verse numbers and the clauses the Berean notes attest. On 16 September 2026 the continuous Greek file passed the structure, Unicode, and Eulexis wordlist checks recorded in the bible-sources quality file (CLEAN, exit 0). The check that runs in this repository is `python3 pipeline/verify.py`.

3 John has 15 verses and Revelation 12 has 18. Those two numbers are Protestant versification supplied by `apply_protestant_coverage.py`. They are not rows in `pipeline/critical_verses.tsv`. The 16 verses on that list are in the body, each with a note. 1 John 5:7–8 in the body is the Scrivener 1894 wording, with an attestation note on verse 7.

This is not a critical edition and not the English Berean Standard Bible. Section headings and parallel references are Berean's. The words of Jesus keep the red marking Berean used.
