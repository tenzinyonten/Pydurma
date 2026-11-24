# Chinese (`zh`)

Chinese support for Pydurma, mostly aimed at classical and Buddhist Chinese (e.g. CBETA texts), for the same whole process as Tibetan: several witnesses of a text (OCR outputs or editions) are aligned, the best reading is selected at each point, and the result is written as one merged text. It provides a tokenizer, a normalizer and a weigher (`ValidZhTokenWeigher`) that plug into the same pipeline as the Tibetan ones.

## Quick start

```python
from Pydurma.zh import merge_chinese, collate_chinese

witnesses = [
    "如是我聞：一時，佛在舍衛國，身ロ意業",
    "如是我聞。一時佛住舍衛國。身口意業",
    "如是我聞一時佛在舍衛國身口意業",
]
print(merge_chinese(witnesses))
# 如是我聞：一時，佛在舍衛國，身口意業

# or get the weighted alignment, for the other serializers (footnotes, CSV...)
weighted_matrix = collate_chinese(witnesses)
```

Both take `normalizer=ChineseNormalizer(...)` for other settings (e.g. adding `jp2t`), `validity_weigher=False` to only use the majority vote, and `rare_characters=False` to turn off the rare-character check. The sections below show the same process step by step.

## Usage: aligning witnesses

```python
from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.zh.tokenizer_zh import ChineseTokenizer
from Pydurma.zh.normalizer_zh import ChineseNormalizer

witnesses = [
    "如是我聞：一時，佛在舍衛國祇樹給孤獨園，與大比丘衆千二百五十人俱。",
    "如是我聞。一時佛在舍衛國祇樹給孤獨園。與大比丘眾千二百五十人俱。",
    "如是我聞一時佛住舍衛國祇樹給孤獨園與大比丘眾千二百五十人",
]

# use the same tokenizer (and so the same encoder) for all witnesses
tokenizer = ChineseTokenizer(Encoder(), ChineseNormalizer())
token_strings, token_lists = [], []
for witness in witnesses:
    token_string, token_list = tokenizer.tokenize(witness)
    token_strings.append(token_string)
    token_lists.append(token_list)

matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)
for row in matrix:
    print(" | ".join(witnesses[i][t[0]:t[1]] if t else "-" for i, t in enumerate(row)))
```

Part of the output:

```
時， | 時 | 時
佛 | 佛 | 佛
在 | 在 | 住      ← real variant
舍 | 舍 | 舍
```

Punctuation differences (`時，` / `時`) and variant characters (`衆` / `眾`) are not reported as variants. Each cell shows the original text of the witness.

## Usage: merging witnesses into one text

The whole process, from the witnesses to the merged text:

```python
from pathlib import Path

from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.zh.tokenizer_zh import ChineseTokenizer
from Pydurma.zh.normalizer_zh import ChineseNormalizer
from Pydurma.weighers.matrix_weigher import TokenMatrixWeigher
from Pydurma.weighers.token_weigher_normalized_count import NormalizedTokenCountWeigher
from Pydurma.weighers.token_weigher_valid_zh import ValidZhTokenWeigher
from Pydurma.serializers.plain_text import PlainTextSerializer
from Pydurma.serializers.md import MdSerializer

# e.g. three OCR outputs of the same page, one file per witness
version_paths = [Path("ocr-1.txt"), Path("ocr-2.txt"), Path("ocr-3.txt")]
witnesses = [
    "如是我聞：一時，佛在舍衛國，身ロ意業",
    "如是我聞。一時佛住舍衛國。身口意業",
    "如是我聞一時佛在舍衛國身口意業",
]

# 1. tokenize and align
normalizer = ChineseNormalizer()
tokenizer = ChineseTokenizer(Encoder(), normalizer)
token_strings, token_lists = [], []
for witness in witnesses:
    token_string, token_list = tokenizer.tokenize(witness)
    token_strings.append(token_string)
    token_lists.append(token_list)
matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)

# 2. weigh the readings
matrix_weigher = TokenMatrixWeigher()
matrix_weigher.add_weigher(NormalizedTokenCountWeigher(normalizer), 1)            # majority vote
matrix_weigher.add_weigher(ValidZhTokenWeigher.from_texts(witnesses, normalizer), 1)  # OCR noise
weighted_matrix = matrix_weigher.get_weight_matrix(matrix)

# 3. write the merged text
print(PlainTextSerializer(weighted_matrix, Path("."), "t235").serialize_matrix())
# or with footnotes for the other readings (sigla for each witness file name)
sigla = {"ocr-1": "A", "ocr-2": "B", "ocr-3": "C"}
print(MdSerializer(weighted_matrix, Path("."), "t235", version_paths, sigla).serialize_matrix())
```

Output:

```
如是我聞：一時，佛在舍衛國，身口意業
如是我聞：[^1]一時，[^2]佛在[^3]舍衛國，[^4]身口[^5]意業

[^1]: 聞：]A: 聞：; B: 聞。; C: 聞;
[^2]: 時，]A: 時，; B,C: 時;
[^3]: 在]A,C: 在; B: 住;
[^4]: 國，]A: 國，; B: 國。; C: 國;
[^5]: 口]A: ロ; B,C: 口;
```

The katakana ロ that the OCR of witness A read for 口 loses (it is outvoted and is not a Chinese character), and so does the minority reading 住. Use `save_serialized_matrix()` to write the output to a file in the given folder. The footnotes for punctuation-only differences come from Pydurma's shared code (see [Known issues](#known-issues-in-pydurmas-shared-code)).

Call the aligner directly as above rather than through `CommonSpeller`, which currently gives one column too many for the footnote serializers.

## How it works

### Tokenizer (`tokenizer_zh.py`)

- **One token per character.** No word segmentation: classical Chinese has no spaces, and modern segmenters (like jieba) are built for Mandarin and can split two witnesses differently because of a single variant character. Character-level comparison is the usual approach for collating Chinese.
- **Punctuation is its own token**, like the shad in the Tibetan tokenizer, so that it is aligned and voted on separately from the characters: with `：` / `。` / `：` in three witnesses, `：` is selected. When a witness has no punctuation at that place, Pydurma's post-processing merges the row into the previous one (it does this for every row with a gap), and the punctuation then follows the character vote. Whitespace alone (e.g. line breaks) is ignored in the diff.
- Letters and digits are also one token per character.
- Token positions refer to the original string, also when the input goes through an `InputFilter` first (e.g. to remove footnote markers like `[1]`).

### Normalizer (`normalizer_zh.py`)

The normalizer never changes the token text: it only builds the form used for comparison.

1. **NFKC** (Python's `unicodedata`): unifies full-width and half-width forms (`Ａ１，` → `A1,`) and CJK compatibility ideographs.
2. **Whitespace is removed**, and punctuation too in tokens that have characters (merged cells). Punctuation-only tokens keep their punctuation, so they can be compared.
3. **Variant characters (異體字) are unified with OpenCC**, using the configs `hk2t` and `tw2t` in that order (e.g. 為→爲, 眾→衆, 說→説, 衛→衞).
4. **A small extra table** for common variants OpenCC misses: 敎→教, 淸→清, 呑→吞, 讃→讚, 眞→真, 卽→即, 綫→線.
5. **Some characters are never converted** (`keep_distinct`), because OpenCC merges them with a character that is a different word in classical Chinese: 台 (pronoun, star name) / 臺 (terrace), 核 (kernel) / 覈 (examine), 參 / 蔘, 才 / 纔 (and with `jp2t`: 余 "I" / 餘 "surplus", 予 / 豫, 党 / 黨).

**OpenCC configs that are not used by default:**

- **`jp2t`** (Japanese shinjitai → traditional, e.g. 仏→佛, 経→經) adds 321 merges over all CJK characters, most of them useful for Japanese editions or OCR, but some between different classical words (余 / 餘, 予 / 豫). Add it for Japanese material; `keep_distinct` still protects those pairs.
- **`t2s` / `s2t`** (traditional ↔ simplified) merge characters that are distinct in classical texts (云/雲, 后/後, 干/乾/幹, 里/裏): `s2t` alone merges 2,580 groups of characters. Use them only if your witnesses mix simplified and traditional script.

### Options

```python
ChineseNormalizer(
    opencc_configs=("hk2t", "tw2t"),  # add "jp2t" for Japanese editions or OCR
    extra_variants=None,               # your own {character: character} table, replaces the default one
    keep_distinct=None,                # characters never converted, replaces the default set
)
```

### Selecting the best reading (weighers)

Two weighers are meant to be used together:

- **`NormalizedTokenCountWeigher(normalizer)`** (`weighers/token_weigher_normalized_count.py`, shared with Sanskrit): majority vote, counting readings by their normalized form. The default `TokenCountWeigher` compares the token text directly, so `衆` / `眾` or `聞：` / `聞。` would split the vote.
- **`ValidZhTokenWeigher`** (`weighers/token_weigher_valid_zh.py`): the counterpart of `ValidBoTokenWeigher` (relative weigher, like the Tibetan one). As OCR always produces real characters, there is no invalid spelling to detect; it looks for two signs of OCR errors instead:
  - **characters that don't belong in a Chinese text** get 70% of their weight: letters that are not Chinese characters (typically Japanese katakana that look like Chinese characters: ロ for 口, エ for 工, カ for 力, ー for 一; or Latin and Hangul letters) and non-ASCII symbols. Private Use Area characters (CBETA's rare characters) are not penalized.
  - **characters that are rare in the document** get 85%: characters that appear only once in all the witnesses together, counted by `ValidZhTokenWeigher.from_texts(witnesses)`. A real character usually appears in every witness, an OCR error often only once. No external frequency list is needed.

On the Diamond Sūtra, `ValidZhTokenWeigher` flags none of the 31,265 tokens of the 5 real editions. Merging 2 simulated OCR outputs (about 60 errors each), it leaves about a third fewer errors than the majority vote alone (40 instead of 60), and settles 1 vs. 1 disagreements on look-alikes and one-off characters. It can't detect errors that produce a common character (未 / 末, 己 / 已): those are left to the majority vote.

**Whether the one-off penalty helps depends on the kind of OCR errors.** When errors produce unusual characters, it is what helps most with 2 witnesses, where the majority vote can't decide (simulation on the Diamond Sūtra: 59 → 40 errors; the look-alike check alone: 59 → 59). When errors produce common characters, it can make things slightly worse, as the correct character is often the rare one: on the Chojuk, where 520 of the 1,593 different characters appear only once, merging 2 witnesses gave 1.03% errors with it against 0.99% without it. Until it is tested on real OCR output, it can be turned off with `rare_characters=False` (or by creating the weigher without `from_texts()`).

### Output (serializers)

All of Pydurma's serializers work with Chinese:

| Serializer | Output |
|---|---|
| `PlainTextSerializer` | the merged text |
| `MdSerializer` | the merged text with footnotes giving the other readings |
| `DocxSerializer` | the same as a Word file (needs `pandoc` installed) |
| `CSVSerializer` | the alignment table with the weight of each reading |
| `HFMLSerializer` | the merged text with notes, in OpenPecha's HFML format |

## Tests and results on real data

- Unit tests: `tests/preprocessor/tokenizer/test_tokenizer_zh.py`, `tests/preprocessor/normalizer/test_normalizer_zh.py`, `tests/aligner/test_zh_alignment.py`, `tests/weighers/test_token_weigher_valid_zh.py`, `tests/weighers/test_token_weigher_normalized_count.py`
- Whole process and outputs: `tests/test_zh_merged_text.py`, `tests/test_zh_collate.py`, `tests/serializers/test_zh_serializers.py`
- Tested on the Bodhicaryāvatāra (Chojuk) from [WeBuddhist](https://webuddhist.com): the Chinese translation 入菩薩行論 (22,433 characters), with witnesses generated from it. 1,674 spelling variations (variant characters, full-width/half-width punctuation) gave no false differences, and merging 3 witnesses with independent OCR-like errors in 1% / 3% of the characters brought the error rate from 1.00% / 2.99% down to 0.07% / 0.53%.

## Limitations

- **The variant table is not complete.** OpenCC (`hk2t`, `tw2t`) and the extra table cover the common pairs; real texts will have more. Add them with `extra_variants`, or replace OpenCC with fuller data (e.g. the Unicode Unihan variant fields or CBETA's variant table) if needed.
- **Variant-character normalization is not covered by the Diamond Sūtra test**: CBETA had already unified variant forms, so it needs witnesses that were not normalized (e.g. OCR output).
- **Transpositions are not detected** (a Pydurma limitation): a change of word order shows up as an omission plus an insertion.
- **Private Use Area characters** (used by CBETA for rare characters with no Unicode code point) align correctly but display as an empty box.
- **Punctuation and variant characters still get footnotes.** `衆` / `眾` or `聞：` / `聞。` count as one reading with `NormalizedTokenCountWeigher`, but the footnote serializers still list them as different readings (see below).
- **Not yet tested on real OCR output.** The weighers were evaluated on editions and simulated OCR errors; real OCR output of Chinese pages is needed to measure how well the merging works.

## Known issues in Pydurma's shared code

These are in code shared by all languages (Tibetan included), not in the Chinese module, and are left unchanged:

- **`CommonSpeller` + `MdSerializer` / `HFMLSerializer` / `DocxSerializer` fail with an `IndexError`.** `CommonSpeller` adds the first witness twice, so its matrix has one more column than there are witness files. Calling the aligner directly (as in the examples above) avoids it.
- **Extra footnotes.** `is_diff_token` (used by the matrix post-processing and the footnote serializers) compares the token text directly, so punctuation-only and variant-character differences get footnotes. It could take the normalizer into account.
- **HFML notes on several characters are not marked with `:`.** `HFMLSerializer` counts syllables with the Tibetan tsheg, so for Chinese it always treats a note as one syllable.
- **`CSVSerializer` writes the file without specifying UTF-8**, which can fail on Windows for Chinese text.
