from pathlib import Path

from Pydurma.sa.tokenizer_sa import SanskritTokenizer
from Pydurma.sa.normalizer_sa import SanskritNormalizer
from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.weighers.matrix_weigher import TokenMatrixWeigher
from Pydurma.weighers.token_weigher_normalized_count import NormalizedTokenCountWeigher
from Pydurma.weighers.token_weigher_valid_sa import ValidSaTokenWeigher
from Pydurma.serializers.plain_text import PlainTextSerializer


def test_valid_tokens():
    weigher = ValidSaTokenWeigher()
    valid = [
        "dha", "rma", "rmma", "kṣe", "tre ", "vaḥ |", "brahma", "dugdha", "śakta", "jña",
        "idhma", "dhyā", "kārtsnya", "rha", "Rāmaḥ", "r̥ṣi", "saṃ", "sañ", "rma-",
        # word-final consonants, and unsandhied spacing
        "vāk", "t ka", "tac ca", "hy a", "ddhy a",
        # Devanagari
        "र्म्म", "क्षे", "वः ।", "ह्य् अ",
        # digits and symbols outside words: footnote numbers, editorial marks
        "सदृशेति१९ ।", "ति ∗",
    ]
    for s in valid:
        assert weigher.is_valid(s) is True, s


def test_invalid_tokens():
    weigher = ValidSaTokenWeigher()
    invalid = [
        "dhka",     # aspirate before a stop
        "hka",      # h before a stop
        "kha h",    # word-final h
        "gta",      # stops that don't agree in voicing
        "kda",
        "dsa",      # voiced stop before a sibilant
        "rrā",      # double r
        "ṃka",      # anusvāra with no vowel before it
        "kṣṭrpna",  # too many consonants
        "vadh",     # word-final aspirate
        "wa",       # not an IAST letter
        "क©र",       # symbol inside a word (OCR noise)
        "ते५पि",     # digit inside a word (OCR reads the avagraha ऽ as ५)
        "५पि",       # digit right before a letter
        "क्ड",       # stops that don't agree in voicing
        "काि",       # vowel sign with no consonant before it
        "रु्",       # virāma after a vowel
    ]
    for s in invalid:
        assert weigher.is_valid(s) is False, s


def test_weights():
    weigher = ValidSaTokenWeigher()
    column = [(0, 2, 1, "dha"), (0, 3, 1, "dhka"), None, (0, 2, 0, "| ")]
    assert weigher.weigh(column) == [100, 70, None, None]


def test_valid_reading_wins_a_tie():
    # two OCR outputs that disagree: the majority vote alone can't decide (1 vs 1),
    # the validity weigher prefers the well-formed reading, whatever the order
    for witnesses in (["dhkarmakṣetre", "dharmakṣetre"], ["dharmakṣetre", "dhkarmakṣetre"]):
        normalizer = SanskritNormalizer()
        tokenizer = SanskritTokenizer(Encoder(), normalizer)
        token_strings, token_lists = [], []
        for witness in witnesses:
            token_str, token_list = tokenizer.tokenize(witness)
            token_strings.append(token_str)
            token_lists.append(token_list)
        matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)
        matrix_weigher = TokenMatrixWeigher()
        matrix_weigher.add_weigher(NormalizedTokenCountWeigher(normalizer), 1)
        matrix_weigher.add_weigher(ValidSaTokenWeigher(normalizer), 1)
        weighted = matrix_weigher.get_weight_matrix(matrix)
        assert PlainTextSerializer(weighted, Path("."), "test").serialize_matrix() == "dharmakṣetre"
