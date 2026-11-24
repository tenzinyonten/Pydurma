import re
from typing import List, Optional

from Pydurma.normalizer import Normalizer
from Pydurma.sa.slp1_filter import slp1_filter
from Pydurma.sa.filters_sa import sanskrit_filters, SANSKRIT_RULES, B_V_RULES, Rule, VOWELS

# anything that is not an SLP1 letter: spaces, daṇḍas, avagraha, digits, punctuation
NON_SLP1_LETTER_RE = re.compile(r"[^A-Za-z~]+")

FINAL_NASALS = "NYRnm"
FINAL_SIBILANTS = "sSzr"


class SanskritNormalizer(Normalizer):
    """
    Normalizer for Sanskrit (see SanskritTokenizer).

    The token text itself is never changed (normalize_always is the identity), so
    the output keeps the original text. Normalization is only applied to the form
    used for comparison: conversion to SLP1, the rules in filters_sa.py, and
    removal of what is not a letter (spaces, daṇḍas, avagraha, punctuation).

    Two methods give the comparison form, for two different inputs:

    - normalize_pre_token_diff(s): s is a token of text that is already in normalized
      SLP1. SanskritTokenizer converts and normalizes the whole text before splitting
      it (several rules look across the space between words), so this only removes
      what is not a letter.
    - normalize_pre_token_comparison(s): s is the original text of a token (Devanagari
      or IAST), e.g. token[3] in a weigher. It converts and normalizes s on its own.
      As tokens are akṣaras that include the consonants after a space, this gives the
      same result as the whole-text normalization in practice.
    """

    def __init__(
        self,
        convert_to_slp1: bool = True,
        apply_rules: bool = True,
        rules: Optional[List[Rule]] = None,
        normalize_b_v: bool = False,
    ):
        """
        convert_to_slp1: set to False if the input is already in SLP1
        apply_rules: set to False to compare the text without the normalization rules
        rules: the normalization rules to apply, in order (default: SANSKRIT_RULES).
               Each rule has a name, so a subset can be chosen, e.g.
               [r for r in SANSKRIT_RULES if r[0] != "doubled consonant after r"]
        normalize_b_v: also treat b and v as the same letter (for manuscripts where
               they are confused; off by default, see B_V_RULES)
        """
        self.convert_to_slp1 = convert_to_slp1
        self.apply_rules = apply_rules
        self.rules = list(SANSKRIT_RULES if rules is None else rules)
        if normalize_b_v:
            self.rules += B_V_RULES

    def to_normalized_slp1(self, arg):
        """
        Returns arg (a string or an InputFilter) wrapped in the input filters for
        conversion to SLP1 and normalization, according to the settings.
        """
        if self.convert_to_slp1:
            arg = slp1_filter(arg)
        if self.apply_rules:
            arg = sanskrit_filters(arg, self.rules)
        return arg

    def normalize_always(self, s: str) -> str:
        return s

    def normalize_pre_token_diff(self, s: str) -> str:
        return NON_SLP1_LETTER_RE.sub("", s)

    def normalize_pre_token_comparison(self, s: str) -> str:
        normalized = self.to_normalized_slp1(s)
        if not isinstance(normalized, str):
            normalized = normalized.get_string()
        res = NON_SLP1_LETTER_RE.sub("", normalized)
        if self.apply_rules and len(res) >= 2 and res[-2] in VOWELS:
            # In the whole-text normalization, a consonant can only end an akṣara
            # (right after its vowel) if a rule turned it into anusvāra or visarga,
            # because of the consonant that starts the next akṣara (sañ|ja from
            # sañjaya, duś|śā from duśśāsana). On a token alone that context is
            # missing, so apply the result directly.
            if res[-1] in FINAL_NASALS:
                res = res[:-1] + "M"
            elif res[-1] in FINAL_SIBILANTS:
                res = res[:-1] + "H"
        return res
