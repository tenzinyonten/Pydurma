from collections import Counter
from pathlib import Path

from Pydurma.zh.tokenizer_zh import ChineseTokenizer
from Pydurma.zh.normalizer_zh import ChineseNormalizer
from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.weighers.matrix_weigher import TokenMatrixWeigher
from Pydurma.weighers.token_weigher_normalized_count import NormalizedTokenCountWeigher
from Pydurma.weighers.token_weigher_valid_zh import ValidZhTokenWeigher, is_foreign
from Pydurma.serializers.plain_text import PlainTextSerializer


def test_foreign_characters():
    for c in "ロエカニートＡa가Ⅰ😀":
        assert is_foreign(c), c
    # Chinese characters, punctuation, digits and Private Use Area characters are fine
    for c in "如口工力二一〇々。，「1１\U000F03CC":
        assert not is_foreign(c), c


def test_weights_without_counts():
    weigher = ValidZhTokenWeigher()
    column = [(0, 1, 1, "口"), (0, 1, 1, "ロ"), (0, 2, 1, "聞："), None, (0, 1, 0, "「")]
    assert weigher.weigh(column) == [100, 70, 100, None, None]


def test_rare_characters():
    texts = ["佛告須菩提", "佛告須菩提", "佛告須菩娑"]
    weigher = ValidZhTokenWeigher.from_texts(texts)
    # 提 appears twice in the texts, 娑 only once
    assert weigher.weigh([(0, 1, 1, "提"), (0, 1, 1, "娑")]) == [100, 85]


def test_rare_characters_counted_by_normalized_form():
    # 衆 and 眾 are counted together
    weigher = ValidZhTokenWeigher.from_texts(["衆", "眾"])
    assert weigher.char_counts == Counter({"衆": 2})
    assert weigher.weigh([(0, 1, 1, "眾")]) == [100]


def merged_text(witnesses):
    normalizer = ChineseNormalizer()
    tokenizer = ChineseTokenizer(Encoder(), normalizer)
    token_strings, token_lists = [], []
    for witness in witnesses:
        token_str, token_list = tokenizer.tokenize(witness)
        token_strings.append(token_str)
        token_lists.append(token_list)
    matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)
    matrix_weigher = TokenMatrixWeigher()
    matrix_weigher.add_weigher(NormalizedTokenCountWeigher(normalizer), 1)
    matrix_weigher.add_weigher(ValidZhTokenWeigher.from_texts(witnesses, normalizer), 1)
    weighted = matrix_weigher.get_weight_matrix(matrix)
    return PlainTextSerializer(weighted, Path("."), "test").serialize_matrix()


def test_katakana_lookalike_loses_a_tie():
    # two OCR outputs that disagree (1 vs 1): ロ (katakana) for 口, whatever the order
    assert merged_text(["身口意業", "身ロ意業"]) == "身口意業"
    assert merged_text(["身ロ意業", "身口意業"]) == "身口意業"


def test_rare_character_loses_a_tie():
    # 娑 appears only once in the two texts, 提 three times
    assert merged_text(["須菩娑言須菩提", "須菩提言須菩提"]) == "須菩提言須菩提"
