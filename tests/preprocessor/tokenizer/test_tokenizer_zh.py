import re

from Pydurma.zh.tokenizer_zh import ChineseTokenizer
from Pydurma.zh.normalizer_zh import ChineseNormalizer
from Pydurma.encoder import Encoder
from Pydurma.input_filters.pattern_filter import PatternInputFilter


def get_tokenizer():
    return ChineseTokenizer(encoder=Encoder(), normalizer=ChineseNormalizer())


def test_tokenizer_zh():
    test_string = "如是我聞：一時，佛"
    # punctuation is its own token, like the shad in the Tibetan tokenizer
    expected_token_list = [
        (0, 1, 1, "如"),
        (1, 2, 1, "是"),
        (2, 3, 1, "我"),
        (3, 4, 1, "聞"),
        (4, 5, 1, "："),
        (5, 6, 1, "一"),
        (6, 7, 1, "時"),
        (7, 8, 1, "，"),
        (8, 9, 1, "佛"),
    ]
    token_str, token_list = get_tokenizer().tokenize(test_string)
    assert token_list == expected_token_list
    # one character in the token string per token
    assert len(token_str) == 9


def test_same_code_for_variants():
    tokenizer = get_tokenizer()
    # 衆/眾 are variants: the token strings must be identical
    token_str_a, _ = tokenizer.tokenize("大比丘衆，千")
    token_str_b, _ = tokenizer.tokenize("大比丘眾，千")
    assert token_str_a == token_str_b
    # 在/住 is a real difference
    token_str_c, _ = tokenizer.tokenize("佛在")
    token_str_d, _ = tokenizer.tokenize("佛住")
    assert token_str_c != token_str_d


def test_punctuation_tokens():
    tokenizer = get_tokenizer()
    # different punctuation marks are different tokens, so they can be voted on
    token_str_a, _ = tokenizer.tokenize("時，佛")
    token_str_b, _ = tokenizer.tokenize("時。佛")
    assert token_str_a != token_str_b
    assert token_str_a[0] == token_str_b[0] and token_str_a[2] == token_str_b[2]
    # full-width and half-width punctuation are the same (NFKC)
    token_str_c, _ = tokenizer.tokenize("時,佛")
    assert token_str_a == token_str_c


def test_leading_punctuation_and_whitespace():
    token_str, token_list = get_tokenizer().tokenize("「如是")
    assert token_list[0] == (0, 1, 1, "「")
    assert len(token_str) == 3
    # whitespace alone (e.g. a line break) is ignored in the diff
    token_str, token_list = get_tokenizer().tokenize("如\n是")
    assert token_list[1] == (1, 2, 0, "\n")
    assert len(token_str) == 2


def test_supplementary_plane_character():
    # U+20000 (𠀀) is outside the Basic Multilingual Plane
    token_str, token_list = get_tokenizer().tokenize("佛\U00020000說")
    assert [t[3] for t in token_list] == ["佛", "\U00020000", "說"]
    assert token_list[1][:2] == (1, 2)


def test_tokenizer_with_filter():
    # positions must refer to the original string after an input filter
    test_string = "如是[1]我聞"
    filtered = PatternInputFilter(test_string, re.compile(r"\[\d+\]"), "")
    _, token_list = get_tokenizer().tokenize(filtered)
    assert [t[3] for t in token_list] == ["如", "是", "我", "聞"]
    assert token_list[2][0] == 5
    assert test_string[token_list[3][0]:token_list[3][1]] == "聞"
