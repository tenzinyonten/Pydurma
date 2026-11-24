from Pydurma.sa.tokenizer_sa import SanskritTokenizer
from Pydurma.sa.normalizer_sa import SanskritNormalizer
from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner


def align(witnesses):
    tokenizer = SanskritTokenizer(encoder=Encoder(), normalizer=SanskritNormalizer())
    token_strings = []
    token_lists = []
    for witness in witnesses:
        token_str, token_list = tokenizer.tokenize(witness)
        token_strings.append(token_str)
        token_lists.append(token_list)
    matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)
    return [[t[3] if t is not None else None for t in row] for row in matrix]


def test_sa_alignment_iast():
    # Bhagavad Gītā 1.1 with compound hyphens, a doubled consonant after r (dharmma),
    # visarga written as s (yuyutsavas) and a real variant (samāgatā)
    witnesses = [
        "dharma-kṣetre kuru-kṣetre samavetā yuyutsavaḥ |",
        "dharmmakṣetre kurukṣetre samavetā yuyutsavaḥ |",
        "dharmakṣetre kurukṣetre samāgatā yuyutsavas",
    ]
    rows = align(witnesses)
    # the cells contain the original text of each witness
    assert rows[0] == ["dha", "dha", "dha"]
    assert rows[1] == ["rma-", "rmma", "rma"]
    assert rows[9] == ["mave", "mave", "māga"]
    assert rows[-1] == ["vaḥ |", "vaḥ |", "vas"]
    assert len(rows) == 15
    assert all(len(row) == 3 for row in rows)


def test_sa_alignment_devanagari():
    witnesses = [
        "धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।",
        "धर्म्मक्षेत्रे कुरुक्षेत्रे समागता युयुत्सवः",
    ]
    rows = align(witnesses)
    assert rows[1] == ["र्म", "र्म्म"]
    assert rows[9] == ["मवे", "माग"]
    assert rows[-1] == ["वः ।", "वः"]
    assert len(rows) == 15


def test_sa_alignment_word_split():
    # different word splitting must not break the alignment
    witnesses = [
        "tad api ca",
        "tadapi ca",
    ]
    rows = align(witnesses)
    assert rows == [["ta", "ta"], ["d a", "da"], ["pi ", "pi "], ["ca", "ca"]]
