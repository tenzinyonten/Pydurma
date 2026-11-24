import re
import unicodedata

import regex
from typing import List, Optional

from Pydurma.tokenizer import Token
from Pydurma.weighers.token_weigher import TokenWeigher
from Pydurma.sa.normalizer_sa import SanskritNormalizer
from Pydurma.sa.filters_sa import CONSONANTS, VOWELS
from Pydurma.sa.slp1_filter import to_slp1

# well-formed Sanskrit according to its phonotactics (which sequences of sounds are
# possible), checked on SLP1. This is meant to catch typical OCR errors (impossible
# consonant clusters, stray signs, foreign letters), not to check spelling.

ASPIRATES = set("KGCJWQTDPB")
UNVOICED_STOPS = set("kKcCwWtTpP")
VOICED_STOPS = set("gGjJqQdDbB")
SIBILANTS = set("sSz")
# consonants that can follow an aspirate or h: semivowels and nasals (brahma, idhma, dhyāna)
AFTER_ASPIRATE_OR_H = set("yrlvnmRN")
MARKS = "MH~"
MAX_CLUSTER = 5  # e.g. kārtsnya: r t s n y

PARTS_RE = re.compile("[" + CONSONANTS + "]+|[" + VOWELS + "][" + MARKS + "]*|[" + MARKS + "]+")
SLP1_LETTERS_RE = re.compile("[" + CONSONANTS + VOWELS + MARKS + "]")

# letters accepted in the original text: Devanagari, and the letters used in IAST
IAST_LETTERS = set("abcdeghijklmnoprstuvyāīūṛṝḷḹṃṁḥṅñṭḍṇśṣḻēō")
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
# a digit or symbol between two letters (or vowel signs, virāma...), or a digit right
# before a letter (e.g. ५पि: footnote numbers come after a word, not before)
DIGIT_OR_SYMBOL_IN_WORD_RE = regex.compile(r"[\p{L}\p{M}][\p{Nd}\p{S}]+[\p{L}\p{M}]|\p{Nd}+[\p{L}\p{M}]")
# Devanagari left after conversion to SLP1, except daṇḍas: a vowel sign or virāma
# with no consonant before it (e.g. का + ि), which can't be correct
UNCONVERTED_DEVANAGARI_RE = re.compile(r"[\u0900-\u0963\u0966-\u097F]")
# consonants before a space and a vowel are the beginning of the next akṣara
# (unsandhied spacing: hy api, tad api), so they are checked with that vowel
CONSONANTS_BEFORE_VOWEL_RE = re.compile("([" + CONSONANTS + r"])\s+(?=[" + VOWELS + "])")


def has_foreign_characters(s: str) -> bool:
    """
    True if s has:
    - letters that are neither Devanagari nor IAST
    - a digit or symbol between two letters, or a digit right before a letter, e.g.
      ते५पि or ते ५पि: OCR often reads the avagraha
      ऽ as the digit ५ (the most common letter-level error in the OCR data of
      Maheshwari et al. 2022), and symbols like © inside a word are OCR noise.
      Digits and symbols elsewhere are accepted: footnote numbers (सदृशेति१९),
      verse numbers, editorial marks after a space (ति ∗).
    """
    s = unicodedata.normalize("NFC", s)
    for c in s:
        if not unicodedata.category(c).startswith("L"):
            continue  # spaces, daṇḍas, punctuation, digits, symbols, combining marks
        if DEVANAGARI_RE.match(c) or c.lower() in IAST_LETTERS:
            continue
        return True
    return DIGIT_OR_SYMBOL_IN_WORD_RE.search(s) is not None


def is_valid_cluster(cluster: str) -> bool:
    """consonants between two vowels in a word"""
    if len(cluster) > MAX_CLUSTER:
        return False
    for x, y in zip(cluster, cluster[1:]):
        if (x in ASPIRATES or x == "h") and y not in AFTER_ASPIRATE_OR_H:
            return False  # e.g. *dhk, *hk, *thth
        if y == "h" and x != "r":
            return False  # a consonant + h is written as an aspirate (kh, gh...), but arhati
        if x == y == "r":
            return False
        x_stop = x in UNVOICED_STOPS or x in VOICED_STOPS
        y_stop = y in UNVOICED_STOPS or y in VOICED_STOPS
        if x_stop and y_stop and ((x in VOICED_STOPS) != (y in VOICED_STOPS)):
            return False  # stops must agree in voicing: *gt, *kd (but dugdha, śakta)
        if (x in VOICED_STOPS and y in SIBILANTS) or (x in SIBILANTS and y in VOICED_STOPS):
            return False  # *ds, *sd
    return True


def is_valid_final(cluster: str) -> bool:
    """consonants at the end of a word"""
    if len(cluster) > 2:
        return False
    return not any(c in ASPIRATES or c == "h" for c in cluster) and (len(cluster) == 1 or is_valid_cluster(cluster))


def is_valid_word_part(part: str) -> bool:
    """
    a part of a token between spaces, in SLP1 letters only. A token is an akṣara,
    so a part is the end of a word (e.g. the "t" of "tat ca") and/or the beginning
    of an akṣara, or several akṣaras for merged cells.
    """
    pieces = PARTS_RE.findall(part)
    if "".join(pieces) != part:
        return False
    for i, piece in enumerate(pieces):
        if piece[0] in MARKS:
            return False  # anusvāra / visarga / candrabindu with no vowel before
        if piece[0] in CONSONANTS:
            if i == len(pieces) - 1:
                # consonants with no vowel after them: the end of a word
                if not is_valid_final(piece):
                    return False
            elif not is_valid_cluster(piece):
                return False
    return True


class ValidSaTokenWeigher(TokenWeigher):
    """
    Returns a weight of:
    - 100 if the token is well-formed Sanskrit
    - weight_invalid (70 by default) if it is not
    - weight_nonsanskrit (None: ignored) if it has no Sanskrit letters (e.g. only punctuation)
    - weight_gap (None: ignored) for a gap

    Like ValidBoTokenWeigher, it is relative by default: an invalid token gets 70%
    of the weight given by the other weighers.

    The checks are done on the SLP1 form of the token as written (without the
    normalization rules), word by word: consonant clusters across a space are not
    checked, as unsandhied texts can have them. The normalizer is only used for its
    convert_to_slp1 setting.
    """

    def __init__(
        self,
        normalizer: Optional[SanskritNormalizer] = None,
        weight_invalid: int = 70,
        weight_nonsanskrit: int = None,
        weight_gap: int = None,
        relative: bool = True,
    ):
        super().__init__(relative)
        self.normalizer = normalizer if normalizer is not None else SanskritNormalizer()
        self.weight_invalid = weight_invalid
        self.weight_nonsanskrit = weight_nonsanskrit
        self.weight_gap = weight_gap

    def is_valid(self, s: str) -> Optional[bool]:
        """True / False, or None if s has no Sanskrit letters"""
        if has_foreign_characters(s):
            return False
        # checked on the text as written, without the normalization rules (they
        # only matter for comparison, and can move a nasal out of its context)
        slp1 = to_slp1(s) if self.normalizer.convert_to_slp1 else s
        if UNCONVERTED_DEVANAGARI_RE.search(slp1):
            return False
        if not SLP1_LETTERS_RE.search(slp1):
            return None
        slp1 = CONSONANTS_BEFORE_VOWEL_RE.sub(r"\1", slp1)
        # anything else that is not a letter separates words
        parts = re.sub("[^" + CONSONANTS + VOWELS + MARKS + "]+", " ", slp1).split()
        return all(is_valid_word_part(part) for part in parts)

    def weigh(self, column: List[Token]) -> List[int]:
        weights = []
        for t in column:
            if t is None or not t[3]:
                weights.append(self.weight_gap)
                continue
            valid = self.is_valid(t[3])
            if valid is None:
                weights.append(self.weight_nonsanskrit)
            elif valid:
                weights.append(100)
            else:
                weights.append(self.weight_invalid)
        return weights
