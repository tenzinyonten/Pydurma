import unicodedata
from collections import Counter
from typing import Iterable, List, Optional

import regex

from Pydurma.tokenizer import Token
from Pydurma.weighers.token_weigher import TokenWeigher
from Pydurma.zh.normalizer_zh import ChineseNormalizer

HAN_RE = regex.compile(r"\p{Han}")


def is_foreign(c: str) -> bool:
    """
    True for characters that should not be in a Chinese text and are typical OCR
    noise: letters (or letter-like numerals) that are not Chinese characters,
    e.g. Japanese katakana that look like Chinese characters (ロ for 口, エ for 工,
    カ for 力, ー for 一), Latin or Hangul letters, and non-ASCII symbols.

    Chinese characters, punctuation, digits and Private Use Area characters (used
    by CBETA for rare characters with no Unicode code point) are not foreign.
    """
    if HAN_RE.match(c):
        return False
    category = unicodedata.category(c)
    if category.startswith("L") or category == "Nl":
        return True
    return category.startswith("S") and ord(c) > 127


class ValidZhTokenWeigher(TokenWeigher):
    """
    The Chinese counterpart of ValidBoTokenWeigher. As OCR always produces real
    characters, there is no "invalid spelling" to detect; instead it returns a
    weight of:

    - weight_invalid (70 by default) if the token has foreign characters (see is_foreign)
    - weight_rare (85 by default) if the token has a character that is rare in the
      document, i.e. appears fewer than min_count times in all the witnesses
      together (only if char_counts is given, see from_texts)
    - 100 otherwise
    - weight_nonchinese (None: ignored) if the token has no Chinese character
      (e.g. punctuation only)
    - weight_gap (None: ignored) for a gap

    Like ValidBoTokenWeigher, it is relative by default: an invalid token gets 70%
    of the weight given by the other weighers.

    The rarity check relies on the fact that a real character usually appears in
    all witnesses (and often several times), while an OCR error that produces an
    unexpected character often appears only once. It does not help when an error
    produces a common character (未 / 末, 己 / 已): that is left to the majority vote.
    """

    def __init__(
        self,
        normalizer: Optional[ChineseNormalizer] = None,
        char_counts: Optional[Counter] = None,
        min_count: int = 2,
        weight_invalid: int = 70,
        weight_rare: int = 85,
        weight_nonchinese: int = None,
        weight_gap: int = None,
        relative: bool = True,
    ):
        super().__init__(relative)
        self.normalizer = normalizer if normalizer is not None else ChineseNormalizer()
        self.char_counts = char_counts
        self.min_count = min_count
        self.weight_invalid = weight_invalid
        self.weight_rare = weight_rare
        self.weight_nonchinese = weight_nonchinese
        self.weight_gap = weight_gap

    @classmethod
    def from_texts(cls, texts: Iterable[str], normalizer: Optional[ChineseNormalizer] = None, **kwargs):
        """
        Returns a weigher with character counts taken from texts (typically all the
        witnesses), counted by normalized form so that variant characters count together.
        """
        normalizer = normalizer if normalizer is not None else ChineseNormalizer()
        counts = Counter()
        for text in texts:
            for c in text:
                counts[normalizer.normalize_pre_token_comparison(c)] += 1
        return cls(normalizer=normalizer, char_counts=counts, **kwargs)

    def is_rare(self, c: str) -> bool:
        if self.char_counts is None:
            return False
        return self.char_counts[self.normalizer.normalize_pre_token_comparison(c)] < self.min_count

    def weigh_string(self, s: str) -> Optional[int]:
        if any(is_foreign(c) for c in s):
            return self.weight_invalid
        chinese = [c for c in s if HAN_RE.match(c) or unicodedata.category(c) == "Co"]
        if not chinese:
            return self.weight_nonchinese
        if any(self.is_rare(c) for c in chinese):
            return self.weight_rare
        return 100

    def weigh(self, column: List[Token]) -> List[int]:
        weights = []
        for t in column:
            if t is None or not t[3]:
                weights.append(self.weight_gap)
            else:
                weights.append(self.weigh_string(t[3]))
        return weights
