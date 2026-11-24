from pathlib import Path

from Pydurma.sa.tokenizer_sa import SanskritTokenizer
from Pydurma.sa.normalizer_sa import SanskritNormalizer
from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.weighers.matrix_weigher import TokenMatrixWeigher
from Pydurma.weighers.token_weigher_count import TokenCountWeigher
from Pydurma.weighers.token_weigher_normalized_count import NormalizedTokenCountWeigher
from Pydurma.serializers.plain_text import PlainTextSerializer


def merged_text(witnesses, weigher):
    """the whole process: tokenize, align, weigh, write the merged text"""
    tokenizer = SanskritTokenizer(Encoder(), SanskritNormalizer())
    token_strings, token_lists = [], []
    for witness in witnesses:
        token_str, token_list = tokenizer.tokenize(witness)
        token_strings.append(token_str)
        token_lists.append(token_list)
    matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)
    matrix_weigher = TokenMatrixWeigher()
    matrix_weigher.add_weigher(weigher, 1)
    weighted = matrix_weigher.get_weight_matrix(matrix)
    return PlainTextSerializer(weighted, Path("."), "test").serialize_matrix()


def test_sa_merged_text_spelling_variants():
    # rma, rmma and rma- are the same reading: 3 witnesses have it, 2 have the error nma
    witnesses = [
        "dhanmakṣetre",
        "dharmakṣetre",
        "dharmmakṣetre",
        "dhanmakṣetre",
        "dharma-kṣetre",
    ]
    # the plain majority vote sees nma (2) > rma, rmma, rma- (1 each)
    assert merged_text(witnesses, TokenCountWeigher()) == "dhanmakṣetre"
    assert merged_text(witnesses, NormalizedTokenCountWeigher(SanskritNormalizer())) == "dharmakṣetre"


def test_sa_merged_text_anusvara():
    # saṃjaya and sañjaya are the same reading, sajjaya is an error
    witnesses = [
        "kim akurvata sajjaya",
        "kim akurvata saṃjaya",
        "kim akurvata sañjaya",
    ]
    # the plain majority vote sees three different readings and keeps the first one
    assert merged_text(witnesses, TokenCountWeigher()) == "kim akurvata sajjaya"
    # counted by normalized form, saṃjaya / sañjaya has 2 votes; the first spelling is written
    assert merged_text(witnesses, NormalizedTokenCountWeigher(SanskritNormalizer())) == "kim akurvata saṃjaya"


def test_sa_merged_text_original_script_and_spelling():
    # the merged text is in the original script and spelling: b is not written v
    witnesses = [
        "ब्रह्म धर्मक्षेत्रे समवेता",
        "ब्रह्म धर्मक्षेत्रे समागता",
        "ब्रह्म धर्म्मक्षेत्रे समवेता",
    ]
    merged = merged_text(witnesses, NormalizedTokenCountWeigher(SanskritNormalizer()))
    assert merged == "ब्रह्म धर्मक्षेत्रे समवेता"
