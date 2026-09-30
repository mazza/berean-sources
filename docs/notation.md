# Greek notation

The Greek text is the Berean Greek Bible (BGB). Its base is Nestle 1904. Berean prints an inline apparatus for words and for word order. This edition keeps one reading in the line and records the rest as notes.

## Abbreviations

The footnotes use the abbreviations Berean prints with the Berean Standard Bible. Their front matter asks readers to see the Berean Bible website for the full account of these sources. The key is [Greek, Hebrew, and Aramaic Sources and Abbreviations](https://en.wikisource.org/wiki/Bible_%28Berean_Standard%29/Greek,_Hebrew_and_Aramaic_Sources_and_Abbreviations):

| Abbreviation | Source |
|---|---|
| NA | Nestle Aland, Novum Testamentum Graece |
| SBL | Society of Biblical Literature, Greek New Testament |
| ECM | Editio Critica Maior, Novum Testamentum Graecum |
| NE | Eberhard Nestle Novum Testamentum Graece |
| WH | Westcott and Hort, New Testament in the Original Greek |
| BYZ | The New Testament in the Original Greek: Byzantine Textform |
| GOC | Greek Orthodox Church, New Testament |
| TR | Scrivener’s Textus Receptus<br>Stephanus Textus Receptus |
| DSS | Dead Sea Scrolls |
| MT | Hebrew Masoretic Text: Westminster Leningrad Codex<br>Hebrew Masoretic Text: Biblia Hebraica Stuttgartensia |
| LXX | Greek OT Septuagint: Rahlfs-Hanhart Septuaginta<br>Greek OT Septuagint: Swete's Septuagint |
| SP | Samaritan Pentateuch |

Abbreviations added in this edition:

| Abbreviation | Source |
|---|---|
| BGB | Berean Greek Bible |

A note names the edition by its abbreviation. The word-order and compound notes begin with BGB. The same Berean abbreviations also appear inside the brackets kept in the line. That legend is the next section.

## Words that stay in the line

A word that is not in Nestle 1904 is marked with the last edition, from left to right, that contains it:

| Mark | Edition |
|---|---|
| `{TR}` | Scrivener, Textus Receptus |
| `⧼BYZ⧽` | Robinson-Pierpont, Byzantine |
| `(WH)` | Westcott and Hort |
| `〈NE〉` | Nestle 1904, when the word is in neither NA nor SBL |
| `[NA]` | Nestle-Aland 28 |
| `‹SBL›` | SBL Greek New Testament |

This file has no `{TR}` braces in the text. Byzantine words use `⧼BYZ⧽` in two places: 1 Corinthians 16:24 and Revelation 22:21. The Nestle brackets are `〈 〉` in the DOCX and `〈 〉` after NFC.

Parentheses and square brackets are not only those sigla. The same characters are ordinary punctuation, and square brackets also enclose a phrase Berean printed that way. They stay as printed.

`« »` belongs to the word-order note below. The guillemets stay in the line.

A star in the DOCX marks a spelling updated from Nestle where NA and SBL agree. The reading keeps that spelling and does not keep the star. The star is not a footnote.

## Word order

Where NA or SBL order the words differently, Berean keeps the Nestle order and marks the other order:

```text
«Nestle order» ⇔ «NA and/or SBL order»
```

The arrow is not always between two guillemet spans. Often it stands between two words, or only one side is in guillemets.

The reading keeps the written order and drops the arrow. A footnote quotes the mark:

```text
BGB marks a word-order variant here: «ἀφιέναι ἁμαρτίας» ⇔ «ἐπὶ τῆς γῆς».
```

The quote takes the guillemet span on each side of the arrow. A comma or a period between the span and the arrow still counts as that span. A side with no guillemets contributes the Greek word on that side. The note does not supply wording the DOCX does not print.

## Compound words

Berean marks a compound-word variant in one of two ways:

```text
Compound ‿ Word
Compound¦word
```

A chain such as `μὲν‿ οὖν‿ γε` is one note. The reading joins on a broken bar and keeps the space of an undertie. The footnote quotes the source:

```text
BGB marks a compound-word variant here: ὅ¦τι.
```

Five marks keep a different spelling. The line uses that reading, and the note still quotes the mark:

| Mark | Reading |
|---|---|
| `ἀγαθὸν¦ποιῆσαι` | `ἀγαθὸν ποιῆσαι` |
| `κάτω¦κύψας` | `κάτω κύψας` |
| `Ἄρα¦Γε` | `Ἄραγε` |
| `Μή¦Ποτε` | `Μήποτε` |
| `καθ‿ εἷς` | `καθ’ εἷς` |

A wrong letter, accent, or breathing in the DOCX is corrected from `pipeline/errata.tsv`. These five readings are not rows there.

A mark at the end of a paragraph quotes the first Greek word of the next line. Acts 4:25 is that case: the line ends at `Ἵνα`, and the note quotes `Ἵνα‿ Τί`.

## Where the notes come from

`pipeline/greek_docx_to_markdown.py` reads `prepared/_work/bgb-edited.docx` and writes the footnotes with the sentences above. `pipeline/build_canon.py` then gives each note its chapter letter. The bracket legend Berean publishes with the Greek text is at [greekbible.org](https://greekbible.org/).
