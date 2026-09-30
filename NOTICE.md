# Notice

This repository is not published by Berean Bible or Bible Hub.

The Hebrew, Aramaic, and Greek wording comes from materials Berean Bible
dedicated to the public domain under CC0 1.0 on 30 April 2023
(https://berean.bible/terms.htm). The downloads this pipeline reads are stored in `archive/` with their
sha256: the Berean tables TSV and the Berean Greek Bible DOCX. Their URLs
are in `manifest.json`. `prepared/` is the continuous Markdown built from
those files. The table in original-language order is
`extra/tables-original-order.tsv`, written by `pipeline/reorder_tables.py`.
That file is word-level morphology. The Markdown export leaves it beside
the reading text.

Verses listed in `pipeline/critical_verses.tsv` are included in the Greek
chapters so the reading is complete. They are not a silent change: each one
has a footnote. Because of them, this text is not a verbatim copy of the
Berean Greek Bible. Berean ask that derivative works not use the Berean
name. The repository is named `berean-sources` to identify the CC0 source, and
the README states that it is not their official text.

The Markdown structuring, the footnote identifiers, and the scripts are
dedicated to the public domain under CC0 1.0 (LICENSE).

`pipeline/verse_limits.tsv` is the Protestant verse maxima from the
Copenhagen Alliance versification file `eng.json`, © Copenhagen Alliance,
licensed CC BY-SA 4.0. It records how many verses each chapter has in that
numbering. It is not Bible wording.
