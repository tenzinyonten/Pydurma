from Pydurma.zh.normalizer_zh import ChineseNormalizer


def test_normalize_always_keeps_original():
    normalizer = ChineseNormalizer()
    assert normalizer.normalize_always("眾，") == "眾，"


def test_punctuation_and_width():
    normalizer = ChineseNormalizer()
    # punctuation is removed from tokens that have characters (e.g. merged cells)
    assert normalizer.normalize_pre_token_diff("聞：") == "聞"
    assert normalizer.normalize_pre_token_diff("時， ") == "時"
    # but kept in punctuation-only tokens, so that they can be compared
    assert normalizer.normalize_pre_token_diff("「") == "「"
    assert normalizer.normalize_pre_token_diff("， ") == normalizer.normalize_pre_token_diff(",")
    # whitespace alone gives nothing
    assert normalizer.normalize_pre_token_diff(" \n") == ""
    # full-width letters and digits become half-width
    assert normalizer.normalize_pre_token_diff("Ａ１") == "A1"


def test_variants_unified():
    normalizer = ChineseNormalizer()
    pairs = ["爲為", "眞真", "衆眾", "說説", "卽即", "羣群", "綫線", "峯峰", "裏裡", "敎教", "淸清", "偽僞", "衛衞"]
    for a, b in pairs:
        assert normalizer.normalize_pre_token_diff(a) == normalizer.normalize_pre_token_diff(b), a + b
    # CJK compatibility ideograph U+F900 is the same as U+8C48 (豈)
    assert normalizer.normalize_pre_token_diff("豈") == normalizer.normalize_pre_token_diff("豈")


def test_distinct_characters_kept_apart():
    normalizer = ChineseNormalizer()
    # merged by t2s / s2t, not used
    pairs = ["云雲", "后後", "干乾", "乾幹", "里裏"]
    # merged by hk2t / tw2t, kept apart with keep_distinct
    pairs += ["台臺", "核覈", "參蔘", "才纔"]
    for a, b in pairs:
        assert normalizer.normalize_pre_token_diff(a) != normalizer.normalize_pre_token_diff(b), a + b


def test_japanese_forms_only_with_jp2t():
    # Japanese shinjitai are not unified by default
    assert ChineseNormalizer().normalize_pre_token_diff("経") != ChineseNormalizer().normalize_pre_token_diff("經")
    normalizer = ChineseNormalizer(opencc_configs=["hk2t", "tw2t", "jp2t"])
    for a, b in ["經経", "觀観", "佛仏"]:
        assert normalizer.normalize_pre_token_diff(a) == normalizer.normalize_pre_token_diff(b), a + b
    # but characters that are different words in classical Chinese stay apart
    for a, b in ["余餘", "予豫", "党黨"]:
        assert normalizer.normalize_pre_token_diff(a) != normalizer.normalize_pre_token_diff(b), a + b


def test_simplified_only_with_t2s():
    assert ChineseNormalizer().normalize_pre_token_diff("闻") != ChineseNormalizer().normalize_pre_token_diff("聞")
    normalizer = ChineseNormalizer(opencc_configs=["t2s"])
    assert normalizer.normalize_pre_token_diff("闻") == normalizer.normalize_pre_token_diff("聞")


def test_extra_variants_can_be_replaced():
    normalizer = ChineseNormalizer(extra_variants={"佛": "仏"})
    assert normalizer.normalize_pre_token_diff("佛") == "仏"
