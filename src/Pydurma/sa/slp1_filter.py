"""
Conversion of Sanskrit text (Devanagari or IAST, or a mix of both) to SLP1.

SLP1 writes every Sanskrit sound with exactly one ASCII character (kh → K, ā → A,
ṣ → z, etc.), which makes syllable splitting and normalization rules much simpler.

The conversion is done with a PatternInputFilter so that positions in the original
text are kept: tokens produced from the SLP1 text still point to the right characters
in the original Devanagari or IAST string.
"""
import re
import unicodedata

from Pydurma.input_filters.pattern_filter import PatternInputFilter

# --- Devanagari ---

DEV_CONSONANTS = {
    "क": "k", "ख": "K", "ग": "g", "घ": "G", "ङ": "N",
    "च": "c", "छ": "C", "ज": "j", "झ": "J", "ञ": "Y",
    "ट": "w", "ठ": "W", "ड": "q", "ढ": "Q", "ण": "R",
    "त": "t", "थ": "T", "द": "d", "ध": "D", "न": "n", "ऩ": "n",
    "प": "p", "फ": "P", "ब": "b", "भ": "B", "म": "m",
    "य": "y", "र": "r", "ऱ": "r", "ल": "l", "ळ": "L", "ऴ": "L", "व": "v",
    "श": "S", "ष": "z", "स": "s", "ह": "h",
    # precomposed nukta forms, nukta is ignored
    "क़": "k", "ख़": "K", "ग़": "g", "ज़": "j", "ड़": "q", "ढ़": "Q", "फ़": "P", "य़": "y",
}

DEV_VOWEL_SIGNS = {
    "ा": "A", "ि": "i", "ी": "I", "ु": "u", "ू": "U", "ृ": "f", "ॄ": "F",
    "ॢ": "x", "ॣ": "X", "ॅ": "e", "ॆ": "e", "े": "e", "ै": "E",
    "ॉ": "o", "ॊ": "o", "ो": "o", "ौ": "O",
    "्": "",  # virāma: no inherent vowel
}

DEV_OTHERS = {
    "अ": "a", "आ": "A", "इ": "i", "ई": "I", "उ": "u", "ऊ": "U",
    "ऋ": "f", "ॠ": "F", "ऌ": "x", "ॡ": "X",
    "ऍ": "e", "ऎ": "e", "ए": "e", "ऐ": "E", "ऑ": "o", "ऒ": "o", "ओ": "o", "औ": "O",
    "ँ": "~", "ं": "M", "ः": "H", "ऽ": "'", "ॐ": "oM",
    "०": "0", "१": "1", "२": "2", "३": "3", "४": "4",
    "५": "5", "६": "6", "७": "7", "८": "8", "९": "9",
}

NUKTA = "़"

# --- IAST (and common ISO 15919 alternatives) ---

IAST = {
    "a": "a", "ā": "A", "i": "i", "ī": "I", "u": "u", "ū": "U",
    "ṛ": "f", "ṝ": "F", "ḷ": "x", "ḹ": "X", "r̥": "f", "r̥̄": "F", "l̥": "x", "l̥̄": "X",
    "e": "e", "ē": "e", "ai": "E", "o": "o", "ō": "o", "au": "O",
    "ṃ": "M", "ṁ": "M", "ḥ": "H", "m̐": "~", "'": "'", "’": "'",
    "k": "k", "kh": "K", "g": "g", "gh": "G", "ṅ": "N",
    "c": "c", "ch": "C", "j": "j", "jh": "J", "ñ": "Y",
    "ṭ": "w", "ṭh": "W", "ḍ": "q", "ḍh": "Q", "ṇ": "R",
    "t": "t", "th": "T", "d": "d", "dh": "D", "n": "n",
    "p": "p", "ph": "P", "b": "b", "bh": "B", "m": "m",
    "y": "y", "r": "r", "l": "l", "ḻ": "L", "v": "v",
    "ś": "S", "ṣ": "z", "s": "s", "h": "h",
}

# accept both precomposed (NFC) and decomposed (NFD) forms of the IAST letters
IAST_LOOKUP = {}
for _key, _value in IAST.items():
    IAST_LOOKUP[unicodedata.normalize("NFC", _key)] = _value
    IAST_LOOKUP[unicodedata.normalize("NFD", _key)] = _value

_dev_consonant_class = "".join(DEV_CONSONANTS.keys())
_dev_sign_class = "".join(DEV_VOWEL_SIGNS.keys())
_iast_alternatives = "|".join(re.escape(k) for k in sorted(IAST_LOOKUP, key=len, reverse=True))
_dev_others_alternatives = "|".join(re.escape(k) for k in DEV_OTHERS)

SLP1_PATTERN = re.compile(
    "(?P<dc>[" + _dev_consonant_class + "])" + NUKTA + "?(?P<ds>[" + _dev_sign_class + "])?"
    + "|(?P<do>" + _dev_others_alternatives + ")"
    + "|(?P<iast>" + _iast_alternatives + ")",
    re.IGNORECASE,
)


def _replace(m: re.Match) -> str:
    if m.group("dc"):
        sign = m.group("ds")
        vowel = "a" if sign is None else DEV_VOWEL_SIGNS[sign]
        return DEV_CONSONANTS[m.group("dc")] + vowel
    if m.group("do"):
        return DEV_OTHERS[m.group("do")]
    iast = m.group("iast")
    return IAST_LOOKUP.get(iast.lower(), IAST_LOOKUP.get(unicodedata.normalize("NFC", iast.lower()), iast))


def slp1_filter(arg) -> PatternInputFilter:
    """
    Returns an input filter converting Devanagari and IAST in arg (a string or an
    InputFilter) to SLP1. Characters that are neither (spaces, daṇḍas, punctuation)
    are kept as they are.
    """
    return PatternInputFilter(arg, SLP1_PATTERN, _replace)


def to_slp1(s: str) -> str:
    """
    Convenience function: convert a string to SLP1 (no position tracking).
    """
    return slp1_filter(s).get_string()
