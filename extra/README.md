# Extra

These files are published with the edition and are not the reading text.
`build_bible.py` joins `canon/` only. Each file besides this note is an
entry in the `extras` list of `manifest.json`, and `pipeline/verify.py`
checks the bytes.

## tables-original-order.tsv

Token and morphology rows from the Berean tables, in original-language
order: Heb Sort, then Greek Sort, then BSB Sort. One row is one word.
The header row is Berean's own header; this file changes the row order.

The table covers the Hebrew and Aramaic Old Testament and the Greek New
Testament in that single order, so its scope is `ot-nt`. Exporting one
testament from `build_bible.py` leaves this file whole.

`pipeline/reorder_tables.py` writes this file from `archive/bsb_tables.tsv`.
The chapter text is built from that same download by a different script.
