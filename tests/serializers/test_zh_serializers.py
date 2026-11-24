from pathlib import Path

from Pydurma.zh.tokenizer_zh import ChineseTokenizer
from Pydurma.zh.normalizer_zh import ChineseNormalizer
from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.weighers.matrix_weigher import TokenMatrixWeigher
from Pydurma.weighers.token_weigher_normalized_count import NormalizedTokenCountWeigher
from Pydurma.weighers.token_weigher_valid_zh import ValidZhTokenWeigher
from Pydurma.serializers.plain_text import PlainTextSerializer
from Pydurma.serializers.md import MdSerializer
from Pydurma.serializers.csv import CSVSerializer
from Pydurma.serializers.hfml import HFMLSerializer
from Pydurma.serializers.docx import DocxSerializer

# the whole process for Chinese, from the witnesses to the outputs of all serializers

WITNESSES = [
    "如是我聞：一時，佛在舍衛國",
    "如是我聞。一時佛住舍衛國",
    "如是我聞一時佛在舍衞國",
]
# the serializers sort the witness paths, the matrix columns must be in the same order
VERSION_PATHS = [Path("A-taisho.txt"), Path("B-song.txt"), Path("C-ming.txt")]
SIGLA = {"A-taisho": "T", "B-song": "S", "C-ming": "M"}


def weighted_matrix():
    normalizer = ChineseNormalizer()
    tokenizer = ChineseTokenizer(Encoder(), normalizer)
    token_strings, token_lists = [], []
    for witness in WITNESSES:
        token_str, token_list = tokenizer.tokenize(witness)
        token_strings.append(token_str)
        token_lists.append(token_list)
    matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)
    matrix_weigher = TokenMatrixWeigher()
    matrix_weigher.add_weigher(NormalizedTokenCountWeigher(normalizer), 1)
    matrix_weigher.add_weigher(ValidZhTokenWeigher.from_texts(WITNESSES, normalizer), 1)
    return matrix_weigher.get_weight_matrix(matrix)


def test_plain_text(tmp_path):
    serializer = PlainTextSerializer(weighted_matrix(), tmp_path, "test")
    serialized = serializer.serialize_matrix()
    assert serialized == "如是我聞：一時，佛在舍衛國"
    output = serializer.save_serialized_matrix(serialized)
    assert output.read_text(encoding="utf-8") == serialized


def test_md(tmp_path):
    serializer = MdSerializer(weighted_matrix(), tmp_path, "test", list(VERSION_PATHS), SIGLA)
    serialized = serializer.serialize_matrix()
    # note: footnotes are also made for punctuation and variant characters (聞：/聞。,
    # 衛/衞), as Pydurma's is_diff_token compares the token text directly
    assert serialized == """如是我聞：[^1]一時，[^2]佛在[^3]舍衛[^4]國

[^1]: 聞：]T: 聞：; S: 聞。; M: 聞;
[^2]: 時，]T: 時，; S,M: 時;
[^3]: 在]T,M: 在; S: 住;
[^4]: 衛]T,S: 衛; M: 衞;
"""
    serializer.save_serialized_matrix(serialized)
    assert (tmp_path / "test.md").read_text(encoding="utf-8") == serialized


def test_csv(tmp_path):
    serializer = CSVSerializer(weighted_matrix(), tmp_path, "test")
    serialized = serializer.serialize_matrix()
    # [selected reading], and the weights: 住 is rare in the witnesses (85% of 33)
    assert serialized[7] == ["[在_66_]", "住_28_", "在_66_"]
    assert serialized[0] == ["[如_100_]", "如_100_", "如_100_"]
    output = serializer.save_serialized_matrix(serialized)
    assert "[在_66_],住_28_,在_66_" in output.read_text()


def test_hfml(tmp_path):
    serializer = HFMLSerializer(weighted_matrix(), tmp_path, "test", list(VERSION_PATHS), SIGLA)
    serialized = serializer.serialize_matrix()
    assert serialized == "如是我聞：(1) <S聞。M聞>一時，(2) <SM時>佛在(3) <S住>舍衛(4) <M衞>國"
    serializer.save_serialized_matrix(serialized)
    assert (tmp_path / "test_hfml.txt").read_text(encoding="utf-8") == serialized


def test_docx_content():
    # the docx file itself is made with pandoc (not installed in CI, see
    # test_docx_serializer.py); its content is the Markdown output
    matrix = weighted_matrix()
    docx = DocxSerializer(matrix, Path("."), "test", list(VERSION_PATHS), SIGLA).serialize_matrix()
    md = MdSerializer(matrix, Path("."), "test", list(VERSION_PATHS), SIGLA).serialize_matrix()
    assert docx == md
