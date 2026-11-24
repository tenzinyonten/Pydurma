# Sanskrit (`sa`)

Sanskrit support for Pydurma, for the same whole process as Tibetan: several witnesses of a text (OCR outputs or editions) are aligned, the best reading is selected at each point, and the result is written as one merged text. It provides a tokenizer, a normalizer and a weigher (`ValidSaTokenWeigher`) that plug into the same pipeline as the Tibetan ones. Input can be in **Devanagari or IAST**; all witnesses of one collation should use the same script (see [Limitations](#limitations)).

## Quick start

```python
from Pydurma.sa import merge_sanskrit, collate_sanskrit

witnesses = [
    "dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |",
    "dharmmakṣetre kurukṣetre samāgatā yuyutsavaḥ |",
    "dhkarmakṣetre kurukṣetre samavetā yuyutsavas",
]
print(merge_sanskrit(witnesses))
# dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |

# or get the weighted alignment, for the other serializers (footnotes, CSV...)
weighted_matrix = collate_sanskrit(witnesses)
```

Both take `normalizer=SanskritNormalizer(...)` for other settings (e.g. `normalize_b_v=True`) and `validity_weigher=False` to only use the majority vote. The sections below show the same process step by step.

## Usage: aligning witnesses

```python
from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.sa.tokenizer_sa import SanskritTokenizer
from Pydurma.sa.normalizer_sa import SanskritNormalizer

witnesses = [
    "dharma-kṣetre kuru-kṣetre samavetā yuyutsavaḥ |",
    "dharmmakṣetre kurukṣetre samavetā yuyutsavaḥ |",
    "dharmakṣetre kurukṣetre samāgatā yuyutsavas",
]

# use the same tokenizer (and so the same encoder) for all witnesses
tokenizer = SanskritTokenizer(Encoder(), SanskritNormalizer())
token_strings, token_lists = [], []
for witness in witnesses:
    token_string, token_list = tokenizer.tokenize(witness)
    token_strings.append(token_string)
    token_lists.append(token_list)

matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)
for row in matrix:
    print(" | ".join(t[3] if t else "-" for t in row))
```

Part of the output:

```
dha   | dha   | dha
rma-  | rmma  | rma     ← hyphen and doubled m after r ignored
...
mave  | mave  | māga    ← real variant
tā    | tā    | tā
...
vaḥ | | vaḥ | | vas     ← visarga = s, daṇḍas ignored
```

Each cell shows the original text of the witness. The same works with Devanagari witnesses.

## Usage: merging witnesses into one text

The whole process, from the witnesses to the merged text:

```python
from pathlib import Path

from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.sa.tokenizer_sa import SanskritTokenizer
from Pydurma.sa.normalizer_sa import SanskritNormalizer
from Pydurma.weighers.matrix_weigher import TokenMatrixWeigher
from Pydurma.weighers.token_weigher_normalized_count import NormalizedTokenCountWeigher
from Pydurma.weighers.token_weigher_valid_sa import ValidSaTokenWeigher
from Pydurma.serializers.plain_text import PlainTextSerializer
from Pydurma.serializers.md import MdSerializer

# e.g. three OCR outputs of the same page, one file per witness
version_paths = [Path("ocr-1.txt"), Path("ocr-2.txt"), Path("ocr-3.txt")]
witnesses = [
    "dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |",
    "dharmmakṣetre kurukṣetre samāgatā yuyutsavaḥ |",
    "dhkarmakṣetre kurukṣetre samavetā yuyutsavas",
]

# 1. tokenize and align
normalizer = SanskritNormalizer()
tokenizer = SanskritTokenizer(Encoder(), normalizer)
token_strings, token_lists = [], []
for witness in witnesses:
    token_string, token_list = tokenizer.tokenize(witness)
    token_strings.append(token_string)
    token_lists.append(token_list)
matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)

# 2. weigh the readings
matrix_weigher = TokenMatrixWeigher()
matrix_weigher.add_weigher(NormalizedTokenCountWeigher(normalizer), 1)  # majority vote
matrix_weigher.add_weigher(ValidSaTokenWeigher(normalizer), 1)          # well-formed Sanskrit
weighted_matrix = matrix_weigher.get_weight_matrix(matrix)

# 3. write the merged text
print(PlainTextSerializer(weighted_matrix, Path("."), "gita").serialize_matrix())
# or with footnotes for the other readings (sigla for each witness file name)
sigla = {"ocr-1": "A", "ocr-2": "B", "ocr-3": "C"}
print(MdSerializer(weighted_matrix, Path("."), "gita", version_paths, sigla).serialize_matrix())
```

Output:

```
dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |
dharma[^1]kṣetre kurukṣetre samave[^2]tā yuyutsavaḥ |[^3]

[^1]: dharma]A: dharma; B: dharmma; C: dhkarma;
[^2]: mave]A,C: mave; B: māga;
[^3]: vaḥ |]A,B: vaḥ |; C: vas;
```

The OCR error *dhkarma* loses (it is outvoted and is not valid Sanskrit), and so does the minority reading *samāgatā*. Use `save_serialized_matrix()` to write the output to a file in the given folder.

Call the aligner directly as above rather than through `CommonSpeller`, which currently gives one column too many for the footnote serializers (see [Known issues](#known-issues-in-pydurmas-shared-code)).

## How it works

Each witness goes through three steps inside `SanskritTokenizer.tokenize()`:

```
original text (Devanagari / IAST)
  → 1. conversion to SLP1          (slp1_filter.py)
  → 2. normalization rules          (filters_sa.py)
  → 3. splitting into akṣaras       (tokenizer_sa.py)
```

Steps 1 and 2 are `PatternInputFilter`s, Pydurma's existing mechanism for changing a text while keeping track of positions in the original. The comparison is done on the converted and normalized text, but **the token text (`token[3]`) is the original text of the akṣara**, like in the Tibetan tokenizer, so the merged text written by the serializers is in the original script and spelling.

### 1. Conversion to SLP1 (`slp1_filter.py`)

SLP1 writes every Sanskrit sound with exactly one ASCII character (`kh` → `K`, `ā` → `A`, `ṣ` → `z`), which makes splitting and normalization rules simple.

- Supports Devanagari and IAST (plus common ISO 15919 forms like `r̥`), precomposed or decomposed Unicode, and capitalized words (`Rāmaḥ` → `rAmaH`).
- Uses a small table (~50 entries) instead of the `indic-transliteration` library, because that library converts whole strings and loses the positions in the original text. The table was checked against `indic-transliteration`: all letters match.
- Daṇḍas, digits and punctuation are kept as they are.
- `to_slp1("...")` converts a string directly, for testing.

### 2. Normalization rules (`filters_sa.py`)

The rules make common spelling differences between manuscripts and editions compare as equal. They run on the whole text, not token by token, because several of them look across the space between two words. In order:

| Rule | Example |
|---|---|
| Compound hyphens removed | *dharma-kṣetre* = *dharmakṣetre* |
| Doubled consonant after r | *dharmma* = *dharma*, *varddhate* = *vardhate* |
| Nasal before a stop = anusvāra | *anta* = *aṃta*, *saṅga* = *saṃga*, *sañjaya* = *saṃjaya* |
| Final m before a consonant = anusvāra | *tam karoti* = *taṃ karoti* |
| Candrabindu = anusvāra | *m̐* = *ṃ* |
| Final s / r = visarga (before a consonant or at a phrase end, not before a vowel) | *devās tatra* = *devāḥ tatra* |
| Visarga written as the following sibilant | *niḥspṛhaḥ* = *nisspṛhaḥ* |
| *Optional:* b = v (`normalize_b_v=True`) | *bana* = *vana* |

Avagraha and daṇḍas need no rule: they are not letters, so the normalizer ignores them.

**b = v is off by default.** b and v are often confused in manuscripts from Bengal, Nepal and Mithila, but treating them as the same hides real distinctions (*bala* "strength" / *vala* "enclosure"), and ब / व is a typical OCR confusion that the majority vote should see. Turn it on for manuscripts where b and v are not distinguished.

**About saktumiva:** [saktumiva](https://github.com/chchch/saktumiva) (GPL-3.0) was used only as a reference for which kinds of variation to handle. These rules are written independently from standard Sanskrit orthography and sandhi, with their own regular expressions, and cover far fewer cases than saktumiva's rules.

### 3. Splitting into akṣaras (`tokenizer_sa.py`)

- **One token per akṣara (syllable):** any number of consonants followed by a vowel, plus an optional anusvāra, visarga or candrabindu (`prakāśātmanaḥ` → `pra | kā | śā | tma | naḥ`). Consonants at the end of the text form their own token (`vāk` → `vā | k`).
- **Akṣaras instead of words**, because sandhi changes word boundaries between witnesses.
- **Spaces are ignored when splitting**, so a word-final consonant joins the next vowel: `tad api` and `tadapi` both give `ta | da | pi`. Witnesses that split words differently still align.

### Normalizer (`normalizer_sa.py`)

The settings are on the normalizer, so that the tokenizer and anything else using the normalizer (e.g. weighers) compare text the same way:

```python
SanskritNormalizer(
    convert_to_slp1=True,   # False if the input is already in SLP1
    apply_rules=True,       # False to compare without the normalization rules
    rules=None,             # the rules to apply, default: SANSKRIT_RULES (filters_sa.py)
    normalize_b_v=False,    # True to also treat b and v as the same letter
)
```

Each rule has a name, so a stricter or more lenient set can be chosen, e.g. without the doubled consonants after r:

```python
from Pydurma.sa.filters_sa import SANSKRIT_RULES

rules = [rule for rule in SANSKRIT_RULES if rule[0] != "doubled consonant after r"]
normalizer = SanskritNormalizer(rules=rules)
```

Rule names: `compound hyphens`, `doubled consonant after r`, `doubled aspirate after r`, `nasal before stop`, `final m before consonant`, `candrabindu`, `final s or r`, `sibilant for visarga` (and `b and v` in `B_V_RULES`). The hyphen rule should be kept first.

- `normalize_pre_token_comparison(text)` gives the comparison form of a token's original text (e.g. `token[3]`): `"र्म्म"`, `"rmma"` and `"rma"` all give `rma`. Checked on the Bhagavad Gītā (chapters 1–2): for all 7,895 tokens it gives the same form as the whole-text normalization used by the alignment.
- `normalize_pre_token_diff(text)` is used internally by the tokenizer on text that is already normalized SLP1.

### 4. Selecting the best reading (weighers)

Two weighers are meant to be used together:

- **`NormalizedTokenCountWeigher(normalizer)`** (`weighers/token_weigher_normalized_count.py`, shared with Chinese): majority vote, counting readings by their normalized form. The default `TokenCountWeigher` compares the token text directly, so *rma* / *rmma* / *rma-* or *saṃ* / *sañ* would split the vote.
- **`ValidSaTokenWeigher(normalizer)`** (`weighers/token_weigher_valid_sa.py`): the counterpart of `ValidBoTokenWeigher`. A token that is not well-formed Sanskrit gets 70% of its weight (relative weigher, like the Tibetan one). It checks Sanskrit phonotactics on the text as written: impossible consonant clusters (aspirate before a stop, consonant before *h*, stops that don't agree in voicing, more than 5 consonants), stray vowel signs, virāma, anusvāra or visarga, aspirates or *h* at the end of a word, letters that are neither Devanagari nor IAST (e.g. an OCR `w`), and digits or symbols inside a word (ते५पि, where OCR read the avagraha as ५). Consonant clusters across a space are not checked, as unsandhied texts can have them.

On the Bhagavad Gītā (20,466 tokens), `ValidSaTokenWeigher` flags 2 tokens of the correct text, both real typos in the source. With two witnesses that disagree (1 vs. 1), it makes the well-formed reading win.

**On real OCR output it catches few errors.** On the 5,000 OCR sentences of [Maheshwari et al. (2022)](https://github.com/ayushbits/pe-ocr-sanskrit), it flags 6.8% of the OCR errors (and 0.09% of correct tokens), against 45% of simulated errors: most real OCR errors still look like valid Sanskrit (a missing anusvāra or vowel sign, ब / व, म / भ). It catches double virāmas, stray signs, and the digit ५ read for the avagraha (ते५पि). So with OCR output, **most errors are fixed by the majority vote across several OCR outputs**; the validity weigher is a small extra, mostly useful to settle 1 vs. 1 disagreements.

### 5. Output (serializers)

All of Pydurma's serializers work with Sanskrit, and write the selected readings in the original script and spelling:

| Serializer | Output |
|---|---|
| `PlainTextSerializer` | the merged text |
| `MdSerializer` | the merged text with footnotes giving the other readings |
| `DocxSerializer` | the same as a Word file (needs `pandoc` installed) |
| `CSVSerializer` | the alignment table with the weight of each reading |
| `HFMLSerializer` | the merged text with notes, in OpenPecha's HFML format |

## Tests and results on real data

- Unit tests: `tests/preprocessor/filters/test_sanskrit_filters.py`, `tests/preprocessor/tokenizer/test_tokenizer_sa.py`, `tests/aligner/test_sa_alignment.py`, `tests/weighers/test_token_weigher_valid_sa.py`, `tests/weighers/test_token_weigher_normalized_count.py`
- Whole process and outputs: `tests/test_sa_merged_text.py`, `tests/test_sa_collate.py`, `tests/serializers/test_sa_serializers.py`
- Tested on the Bodhicaryāvatāra (Chojuk) from [WeBuddhist](https://webuddhist.com): the Sanskrit original (76,724 characters), with witnesses generated from it. 2,500 realistic spelling variations (anusvāra, doubled consonants after r, visarga, candrabindu, avagraha, daṇḍas) gave no false differences, and merging 3 witnesses with independent OCR-like errors in 1% / 3% of the letters brought the error rate from 1.10% / 3.31% down to 0.16% / 1.27%. With 2 witnesses, `ValidSaTokenWeigher` brought it from 1.11% / 3.29% (majority vote only) down to 0.84% / 2.63%.

## Limitations

- **All witnesses of one collation should use the same script** (all Devanagari or all IAST). The alignment itself works across scripts, but Pydurma's shared code (the matrix post-processing, `is_diff_token`, the weighers and serializers) compares the token text directly, and `ध` and `dha` are different text. For OCR outputs of the same pages this is always the case. To collate witnesses in different scripts, convert them to one script first.
- **Spelling variants still get footnotes.** For the same reason, `saṃjaya` / `sañjaya` align correctly and count as one reading with `NormalizedTokenCountWeigher`, but the footnote serializers still list them as different readings.
- **Merging only helps if the OCR outputs make different errors.** Tested on 21 real pages from [Maheshwari et al. (2022)](https://github.com/ayushbits/pe-ocr-sanskrit), OCR'd with 3 Tesseract models: the merge (15.14% character error rate) does not beat the best single model (14.97%), because at 10% of the places all 3 models are wrong, and where only one is right the vote can't tell which. **Put the most reliable witness first**: ties go to the first witness (17.81% with a weaker model first). Taking the reliability of each witness into account could get closer to the best possible choice (12.62%); Pydurma doesn't do it yet.
- **Vowel sandhi is not handled:** *jīrṇāni anyāni* vs. *jīrṇāny anyāni*, or *tatra api* vs. *tatrāpi*, show up as variants.
- **-aḥ → -o before voiced consonants is not handled:** *rāmaḥ gacchati* vs. *rāmo gacchati*.
- **Nasal before nasal is deliberately not normalized:** *enaṃ manyate* vs. *enan manyate* shows up as a variant, because a rule for it would also merge real grammatical differences like *tān* / *tām*.
- **Only Devanagari and IAST input.** Other scripts (e.g. Śāradā, Grantha) or other romanizations (Harvard-Kyoto, Velthuis) are not converted.
- **Transpositions are not detected** (a Pydurma limitation): a change of word order shows up as an omission plus an insertion.

## Known issues in Pydurma's shared code

These are in code shared by all languages (Tibetan included), not in the Sanskrit module, and are left unchanged:

- **`CommonSpeller` + `MdSerializer` / `HFMLSerializer` / `DocxSerializer` fail with an `IndexError`.** `CommonSpeller` adds the first witness twice, so its matrix has one more column than there are witness files. Calling the aligner directly (as in the examples above) avoids it.
- **Extra footnotes.** `is_diff_token` (used by the matrix post-processing and the footnote serializers) compares the token text directly, so spelling-only differences get footnotes. It could take the normalizer into account.
- **HFML notes on several akṣaras are not marked with `:`.** `HFMLSerializer` counts syllables with the Tibetan tsheg, so for Sanskrit it always treats a note as one syllable.
- **`CSVSerializer` writes the file without specifying UTF-8**, which can fail on Windows for non-ASCII text.
