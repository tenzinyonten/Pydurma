import re
import unicodedata
from typing import Dict, Iterable, Optional

import opencc

from Pydurma.normalizer import Normalizer

# OpenCC configs applied in order. hk2t and tw2t map Hong Kong / Taiwan standard
# forms to the OpenCC standard traditional form (e.g. 為→爲, 眾→衆, 說→説).
#
# Not used by default:
# - jp2t (Japanese shinjitai to traditional): useful for Japanese editions or OCR
#   (仏→佛, 経→經), but it merges characters that are different words in classical
#   Chinese, like 余 ("I") / 餘 ("surplus") or 予 / 豫. Add it with opencc_configs.
# - t2s / s2t (traditional / simplified): they merge characters that are distinct in
#   classical texts (云/雲, 后/後, 干/乾/幹, 里/裏), which would hide real variants.
DEFAULT_OPENCC_CONFIGS = ("hk2t", "tw2t")

# Common variant pairs that the OpenCC configs above don't unify.
DEFAULT_EXTRA_VARIANTS = {
    "敎": "教",
    "淸": "清",
    "呑": "吞",
    "讃": "讚",
    "眞": "真",
    "卽": "即",
    "綫": "線",  # unified by recent OpenCC versions, not by 1.2 (used on Python 3.8)
}

# Characters that are never converted, because OpenCC merges them with a character
# that is a different word in classical Chinese: 台 (pronoun, star name) / 臺 (terrace),
# 核 (kernel) / 覈 (examine), 參 / 蔘, 才 / 纔, and with jp2t 余 / 餘, 予 / 豫, 党 / 黨.
DEFAULT_KEEP_DISTINCT = set("台臺核覈參蔘才纔余餘予豫党黨")

WHITESPACE_RE = re.compile(r"\s+")
# punctuation and other non-word characters (including variation selectors)
NON_WORD_RE = re.compile(r"[\W_]+")


class ChineseNormalizer(Normalizer):
    """
    Normalizer for Chinese (mostly classical / Buddhist Chinese).

    The token text itself is never changed (normalize_always is the identity), so the
    output keeps the original characters. Normalization is only applied to the form
    used for comparison:

    - NFKC: full-width / half-width forms and CJK compatibility ideographs
    - removal of whitespace
    - variant characters (異體字) unified with OpenCC and a small extra table,
      except for the characters in keep_distinct
    - removal of punctuation, except in tokens that only have punctuation (so that
      punctuation tokens can still be compared and voted on)
    """

    def __init__(
        self,
        opencc_configs: Iterable[str] = DEFAULT_OPENCC_CONFIGS,
        extra_variants: Optional[Dict[str, str]] = None,
        keep_distinct: Optional[Iterable[str]] = None,
    ):
        """
        opencc_configs: OpenCC config names applied in order. Add "jp2t" for Japanese
                        editions or OCR, use ["t2s"] only if witnesses mix simplified
                        and traditional script.
        extra_variants: character → character mapping applied after OpenCC.
                        Defaults to DEFAULT_EXTRA_VARIANTS.
        keep_distinct: characters that are never converted. Defaults to DEFAULT_KEEP_DISTINCT.
        """
        self.converters = [opencc.OpenCC(config) for config in opencc_configs]
        self.extra_variants = DEFAULT_EXTRA_VARIANTS if extra_variants is None else extra_variants
        self.keep_distinct = DEFAULT_KEEP_DISTINCT if keep_distinct is None else set(keep_distinct)
        self._cache: Dict[str, str] = {}

    def normalize_always(self, s: str) -> str:
        return s

    def normalize_char(self, c: str) -> str:
        if c in self.keep_distinct:
            return c
        for converter in self.converters:
            c = converter.convert(c)
        return self.extra_variants.get(c, c)

    def normalize_for_comparison(self, s: str) -> str:
        res = self._cache.get(s)
        if res is not None:
            return res
        res = WHITESPACE_RE.sub("", unicodedata.normalize("NFKC", s))
        without_punctuation = NON_WORD_RE.sub("", res)
        if without_punctuation:
            res = without_punctuation
        res = "".join(self.normalize_char(c) for c in res)
        self._cache[s] = res
        return res

    def normalize_pre_token_diff(self, s: str) -> str:
        return self.normalize_for_comparison(s)

    def normalize_pre_token_comparison(self, s: str) -> str:
        return self.normalize_for_comparison(s)
