import re

from Pydurma.sa.tokenizer_sa import SanskritTokenizer
from Pydurma.sa.normalizer_sa import SanskritNormalizer
from Pydurma.encoder import Encoder
from Pydurma.input_filters.pattern_filter import PatternInputFilter
from Pydurma.utils.utils import token_row_to_text_row


def get_tokenizer(**kwargs):
    return SanskritTokenizer(encoder=Encoder(), normalizer=SanskritNormalizer(**kwargs))


def test_tokenizer_sa_iast():
    test_string = "prakāśātmanaḥ"
    token_str, token_list = get_tokenizer().tokenize(test_string)
    assert [t[3] for t in token_list] == ["pra", "kā", "śā", "tma", "naḥ"]
    assert len(token_str) == 5


def test_tokenizer_sa_devanagari():
    test_string = "धर्मक्षेत्रे ॥"
    _, token_list = get_tokenizer().tokenize(test_string)
    # the token text is the original Devanagari
    assert [t[3] for t in token_list] == ["ध", "र्म", "क्षे", "त्रे ॥"]
    # and positions refer to the original text
    assert token_row_to_text_row(token_list, test_string) == ["ध", "र्म", "क्षे", "त्रे ॥"]


def test_token_text_is_not_normalized():
    # the normalization rules only apply to the comparison, not to the token text
    _, token_list = get_tokenizer().tokenize("brahma dharmma")
    assert "".join(t[3] for t in token_list) == "brahma dharmma"


def test_spaces_ignored_in_splitting():
    tokenizer = get_tokenizer()
    token_str_a, token_list_a = tokenizer.tokenize("tad api")
    token_str_b, _ = tokenizer.tokenize("tadapi")
    assert [t[3] for t in token_list_a] == ["ta", "d a", "pi"]
    assert token_str_a == token_str_b


def test_final_consonant():
    _, token_list = get_tokenizer().tokenize("vāk")
    assert [t[3] for t in token_list] == ["vā", "k"]


def test_dandas_and_avagraha_ignored():
    tokenizer = get_tokenizer()
    token_str_a, _ = tokenizer.tokenize("te 'pi |")
    token_str_b, _ = tokenizer.tokenize("te pi")
    assert token_str_a == token_str_b
    _, token_list = tokenizer.tokenize("| rāma")
    assert token_list[0] == (0, 2, 0, "| ")


def test_same_code_across_scripts_and_variants():
    tokenizer = get_tokenizer()
    token_str_a, _ = tokenizer.tokenize("dharmakṣetre yuyutsavaḥ")
    token_str_b, _ = tokenizer.tokenize("धर्म्मक्षेत्रे युयुत्सवः")
    assert token_str_a == token_str_b


def test_rules_can_be_turned_off():
    tokenizer = get_tokenizer(apply_rules=False)
    token_str_a, _ = tokenizer.tokenize("dharma")
    token_str_b, _ = tokenizer.tokenize("dharmma")
    assert token_str_a != token_str_b


def test_input_already_in_slp1():
    _, token_list = get_tokenizer(convert_to_slp1=False).tokenize("Darma")
    assert [t[3] for t in token_list] == ["Da", "rma"]


def test_tokenizer_with_caller_filter():
    # like in the Tibetan tokenizer, the token text is the text after the caller's
    # filters, and positions refer to the original string
    test_string = "dharma[1]kṣetre"
    filtered = PatternInputFilter(test_string, re.compile(r"\[\d+\]"), "")
    _, token_list = get_tokenizer().tokenize(filtered)
    assert [t[3] for t in token_list] == ["dha", "rma", "kṣe", "tre"]
    assert test_string[token_list[2][0]:token_list[2][1]] == "kṣe"


def test_comparison_form_from_original_text():
    normalizer = SanskritNormalizer()
    # the comparison form of a token's original text, as used by weighers
    assert normalizer.normalize_pre_token_comparison("र्म्म") == normalizer.normalize_pre_token_comparison("rma")
    assert normalizer.normalize_pre_token_comparison("saṃ") == normalizer.normalize_pre_token_comparison("sañ")
    assert normalizer.normalize_pre_token_comparison("vaḥ |") == normalizer.normalize_pre_token_comparison("vas")
    assert normalizer.normalize_pre_token_comparison("dha") != normalizer.normalize_pre_token_comparison("da")
