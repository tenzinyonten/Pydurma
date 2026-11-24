from pathlib import Path

from Pydurma.sa.tokenizer_sa import SanskritTokenizer
from Pydurma.sa.normalizer_sa import SanskritNormalizer
from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.weighers.matrix_weigher import TokenMatrixWeigher
from Pydurma.weighers.token_weigher_normalized_count import NormalizedTokenCountWeigher
from Pydurma.weighers.token_weigher_valid_sa import ValidSaTokenWeigher
from Pydurma.serializers.plain_text import PlainTextSerializer
from Pydurma.serializers.md import MdSerializer
from Pydurma.serializers.csv import CSVSerializer
from Pydurma.serializers.hfml import HFMLSerializer
from Pydurma.serializers.docx import DocxSerializer

# the whole process for Sanskrit, from the witnesses to the outputs of all serializers

IAST = [
    "dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |",
    "dharmmakṣetre kurukṣetre samāgatā yuyutsavaḥ |",
    "dhkarmakṣetre kurukṣetre samavetā yuyutsavas",  # with an OCR error (dhk)
]
DEVANAGARI = [
    "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।",
    "धर्म्मक्षेत्रे कुरुक्षेत्रे समागता युयुत्सवः ।",
    "ध्कर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः",
]
# the serializers sort the witness paths, the matrix columns must be in the same order
VERSION_PATHS = [Path("A-ed1.txt"), Path("B-ed2.txt"), Path("C-ocr.txt")]
SIGLA = {"A-ed1": "A", "B-ed2": "B", "C-ocr": "C"}


def weighted_matrix(witnesses):
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
    return matrix_weigher.get_weight_matrix(matrix)


def test_plain_text(tmp_path):
    serializer = PlainTextSerializer(weighted_matrix(IAST), tmp_path, "test")
    serialized = serializer.serialize_matrix()
    assert serialized == "dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |"
    output = serializer.save_serialized_matrix(serialized)
    assert output.read_text(encoding="utf-8") == serialized
    # the merged text is in the original script
    devanagari = PlainTextSerializer(weighted_matrix(DEVANAGARI), tmp_path, "test").serialize_matrix()
    assert devanagari == "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।"


def test_md(tmp_path):
    serializer = MdSerializer(weighted_matrix(IAST), tmp_path, "test", list(VERSION_PATHS), SIGLA)
    serialized = serializer.serialize_matrix()
    # note: footnotes are also made for spelling variants (dharma/dharmma, vaḥ/vas),
    # as Pydurma's is_diff_token compares the token text directly
    assert serialized == """dharma[^1]kṣetre kurukṣetre samave[^2]tā yuyutsavaḥ |[^3]

[^1]: dharma]A: dharma; B: dharmma; C: dhkarma;
[^2]: mave]A,C: mave; B: māga;
[^3]: vaḥ |]A,B: vaḥ |; C: vas;
"""
    serializer.save_serialized_matrix(serialized)
    assert (tmp_path / "test.md").read_text(encoding="utf-8") == serialized


def test_csv(tmp_path):
    serializer = CSVSerializer(weighted_matrix(IAST), tmp_path, "test")
    serialized = serializer.serialize_matrix()
    # [selected reading], and the weights: dhkarma is not valid Sanskrit (70% of 33)
    assert serialized[0] == ["[dharma_66_]", "dharmma_66_", "dhkarma_23_"]
    assert serialized[1] == ["[kṣe_100_]", "kṣe_100_", "kṣe_100_"]
    output = serializer.save_serialized_matrix(serialized)
    assert "[dharma_66_],dharmma_66_,dhkarma_23_" in output.read_text(encoding="utf-8")


def test_hfml(tmp_path):
    serializer = HFMLSerializer(weighted_matrix(IAST), tmp_path, "test", list(VERSION_PATHS), SIGLA)
    serialized = serializer.serialize_matrix()
    # note: HFML marks notes on several syllables with ":", but the HFML serializer
    # detects syllables with the Tibetan tsheg, so it is never added here (dharma, samave)
    assert serialized == "dharma(1) <BdharmmaCdhkarma>kṣetre kurukṣetre samave(2) <Bmāga>tā yuyutsavaḥ |(3) <Cvas>"
    serializer.save_serialized_matrix(serialized)
    assert (tmp_path / "test_hfml.txt").read_text(encoding="utf-8") == serialized


def test_docx_content():
    # the docx file itself is made with pandoc (not installed in CI, see
    # test_docx_serializer.py); its content is the Markdown output
    matrix = weighted_matrix(IAST)
    docx = DocxSerializer(matrix, Path("."), "test", list(VERSION_PATHS), SIGLA).serialize_matrix()
    md = MdSerializer(matrix, Path("."), "test", list(VERSION_PATHS), SIGLA).serialize_matrix()
    assert docx == md
