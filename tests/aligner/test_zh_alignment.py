from Pydurma.zh.tokenizer_zh import ChineseTokenizer
from Pydurma.zh.normalizer_zh import ChineseNormalizer
from Pydurma.encoder import Encoder
from Pydurma.aligners.fdmp import FDMPaligner


def align(witnesses):
    tokenizer = ChineseTokenizer(encoder=Encoder(), normalizer=ChineseNormalizer())
    token_strings = []
    token_lists = []
    for witness in witnesses:
        token_str, token_list = tokenizer.tokenize(witness)
        token_strings.append(token_str)
        token_lists.append(token_list)
    matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)
    return [[t[3] if t is not None else None for t in row] for row in matrix]


def test_zh_alignment():
    # opening of the Diamond Sutra (T235), with differences in punctuation,
    # a variant character (衆/眾), a real variant (在/住) and a missing character (俱)
    witnesses = [
        "如是我聞：一時，佛在舍衛國祇樹給孤獨園，與大比丘衆千二百五十人俱。",
        "如是我聞。一時佛在舍衛國祇樹給孤獨園。與大比丘眾千二百五十人俱。",
        "「如是我聞一時佛住舍衛國祇樹給孤獨園與大比丘眾千二百五十人",
    ]
    rows = align(witnesses)
    # the opening quote of the third witness has its own row
    assert rows[0] == ["", "", "「"]
    assert rows[1] == ["如", "如", "如"]
    # punctuation missing in a witness: Pydurma's post-processing merges a row with a
    # gap into the previous row, so the punctuation stays with the character
    assert rows[4] == ["聞：", "聞。", "聞"]
    assert rows[8] == ["在", "在", "住"]
    assert rows[22] == ["衆", "眾", "眾"]
    assert rows[-1] == ["人俱。", "人俱。", "人"]
    # every row has exactly one token per witness, and all characters are aligned
    assert len(rows) == 29
    assert all(len(row) == 3 for row in rows)


def test_zh_alignment_punctuation_row():
    # when all witnesses have punctuation, it has its own row
    rows = align(["佛告須菩提：善", "佛告須菩提。善", "佛告須菩提：善"])
    assert rows == [["佛"] * 3, ["告"] * 3, ["須"] * 3, ["菩"] * 3, ["提"] * 3, ["：", "。", "："], ["善"] * 3]


def test_zh_alignment_insertion():
    witnesses = [
        "佛告須菩提",
        "佛告長老須菩提",
    ]
    rows = align(witnesses)
    assert ["佛", "佛"] in rows
    assert ["須", "須"] in rows
    # the two extra characters of the second witness are kept with their neighbour
    assert "".join(row[1] for row in rows) == "佛告長老須菩提"
    assert "".join(row[0] or "" for row in rows) == "佛告須菩提"
