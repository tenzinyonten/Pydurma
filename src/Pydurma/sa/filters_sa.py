"""
Normalization rules for Sanskrit, applied to SLP1 text.

These rules make common spelling variants of manuscripts and editions compare as
equal. They are written from the rules of Sanskrit orthography and sandhi, and are
applied as PatternInputFilters on the whole text (not per token) because several of
them look across the space between two words. Positions in the original text are kept.

Avagraha and daṇḍas don't need a rule: they are not letters, so the normalizer
ignores them when comparing tokens.
"""
import re
from typing import List, Tuple, Callable

from Pydurma.input_filters.pattern_filter import PatternInputFilter

CONSONANTS = "kKgGNcCjJYwWqQRtTdDnpPbBmyrlvSzshL"
VOWELS = "aAiIuUfFxXeEoO"
STOPS = "kKgGcCjJwWqQtTdDpPbB"

ASPIRATES = {"k": "K", "g": "G", "c": "C", "j": "J", "w": "W", "q": "Q", "t": "T", "d": "D", "p": "P", "b": "B"}

Rule = Tuple[str, "re.Pattern", Callable[["re.Match"], str]]

SANSKRIT_RULES: List[Rule] = [
    # 0. some editions separate the members of compounds with hyphens:
    #    dharma-kṣetre → dharmakṣetre (must run first, the other rules rely on it)
    (
        "compound hyphens",
        re.compile(r"(?<=[A-Za-z~])-(?=[A-Za-z~])"),
        lambda m: "",
    ),
    # 1. consonants are often doubled after r: dharmma → dharma, kārtta → kārta,
    #    and an unaspirated consonant before its aspirate: varddhate → vardhate
    (
        "doubled consonant after r",
        re.compile(r"r([kgcjwqtdpbmnyvlRNYSzs])\1"),
        lambda m: "r" + m.group(1),
    ),
    (
        "doubled aspirate after r",
        re.compile(r"r(kK|gG|cC|jJ|wW|qQ|tT|dD|pP|bB)"),
        lambda m: "r" + m.group(1)[1],
    ),
    # 2. a nasal before a stop can be written as anusvāra: anta → aṃta, saṅga → saṃga
    (
        "nasal before stop",
        re.compile("[NYRnm](?=[" + STOPS + "])"),
        lambda m: "M",
    ),
    #    word-final m before a consonant: tam karoti → taṃ karoti
    (
        "final m before consonant",
        re.compile(r"m(?=\s+[" + CONSONANTS + "])"),
        lambda m: "M",
    ),
    #    candrabindu → anusvāra
    (
        "candrabindu",
        re.compile("~"),
        lambda m: "M",
    ),
    # 3. word-final s / r and visarga: devās tatra → devāḥ tatra, punar | → punaḥ |
    #    Not before a vowel, where r is the correct sandhi form and must match the
    #    same text written without a space: buddhir ayuktasya = buddhirayuktasya
    (
        "final s or r",
        re.compile(r"[sr](?=\s+[" + CONSONANTS + r"]|\s*[^A-Za-z~\s]|\s*$)"),
        lambda m: "H",
    ),
    #    visarga before a sibilant is often written as that sibilant: niḥspṛhaḥ = nisspṛhaḥ
    (
        "sibilant for visarga",
        re.compile(r"s(?=s)|S(?=S)|z(?=z)"),
        lambda m: "H",
    ),
]

# Optional: b and v are often confused in manuscripts (especially from Bengal, Nepal
# and Mithila). Not applied by default: it hides real distinctions (bala / vala),
# and ब / व is a typical OCR confusion that the majority vote should see.
# Enable it with SanskritNormalizer(normalize_b_v=True).
B_V_RULES: List[Rule] = [
    (
        "b and v",
        re.compile("b"),
        lambda m: "v",
    ),
]


def sanskrit_filters(arg, rules: List[Rule] = SANSKRIT_RULES):
    """
    Returns arg (a string or an InputFilter on SLP1 text) wrapped in one
    PatternInputFilter per normalization rule. The order of the rules matters.
    """
    for _, pattern, replacement in rules:
        arg = PatternInputFilter(arg, pattern, replacement)
    return arg
