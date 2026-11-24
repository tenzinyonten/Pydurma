from pathlib import Path

from Pydurma.zh.tokenizer_zh import ChineseTokenizer
from Pydurma.zh.normalizer_zh import ChineseNormalizer
from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.weighers.matrix_weigher import TokenMatrixWeigher
from Pydurma.weighers.token_weigher_count import TokenCountWeigher
from Pydurma.weighers.token_weigher_normalized_count import NormalizedTokenCountWeigher
from Pydurma.serializers.plain_text import PlainTextSerializer


def merged_text(witnesses, weigher):
    """the whole process: tokenize, align, weigh, write the merged text"""
    normalizer = ChineseNormalizer()
    tokenizer = ChineseTokenizer(Encoder(), normalizer)
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


def test_zh_merged_text_variant_characters():
    # 衆 and 眾 are the same character: 3 witnesses have it, 2 have the OCR error 家
    witnesses = [
        "與大比丘家俱",
        "與大比丘衆俱",
        "與大比丘眾俱",
        "與大比丘家俱",
        "與大比丘眾俱",
    ]
    # the plain majority vote sees 家 (2) > 眾 (2, tie, first one wins) and 衆 (1)
    assert merged_text(witnesses, TokenCountWeigher()) == "與大比丘家俱"
    # counted by normalized form, 衆/眾 has 3 votes
    assert merged_text(witnesses, NormalizedTokenCountWeigher(ChineseNormalizer())) == "與大比丘衆俱"


def test_zh_merged_text_punctuation():
    # punctuation differences must not split the vote for 聞 against the OCR error 問
    witnesses = [
        "如是我問一時",
        "如是我聞：一時",
        "如是我聞。一時",
    ]
    assert merged_text(witnesses, TokenCountWeigher()) == "如是我問一時"
    assert merged_text(witnesses, NormalizedTokenCountWeigher(ChineseNormalizer())) == "如是我聞：一時"


def test_zh_merged_text_punctuation_vote():
    # the punctuation is voted on separately from the characters: 2 witnesses have ：
    witnesses = [
        "佛告須菩提。善",
        "佛告須菩提：善",
        "佛告須菩提：善",
    ]
    assert merged_text(witnesses, NormalizedTokenCountWeigher(ChineseNormalizer())) == "佛告須菩提：善"


def test_zh_merged_text_keeps_original_characters():
    witnesses = [
        "佛在舍衛國",
        "佛住舍衛國",
        "佛在舍衛國",
    ]
    assert merged_text(witnesses, NormalizedTokenCountWeigher(ChineseNormalizer())) == "佛在舍衛國"
