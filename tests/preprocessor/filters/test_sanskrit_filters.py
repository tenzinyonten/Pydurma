import unicodedata

from Pydurma.sa.slp1_filter import slp1_filter, to_slp1
from Pydurma.sa.filters_sa import sanskrit_filters, SANSKRIT_RULES, B_V_RULES
from Pydurma.sa.normalizer_sa import SanskritNormalizer


def normalize(s):
    return sanskrit_filters(slp1_filter(s)).get_string()


def test_devanagari_to_slp1():
    assert to_slp1("धर्मक्षेत्रे कुरुक्षेत्रे") == "Darmakzetre kurukzetre"
    assert to_slp1("सिद्धिः ऋषिः ज्ञानं") == "sidDiH fziH jYAnaM"
    assert to_slp1("तेऽपि") == "te'pi"
    assert to_slp1("वाक्") == "vAk"
    # daṇḍas are kept as they are
    assert to_slp1("सञ्जय ॥") == "saYjaya ॥"


def test_iast_to_slp1():
    assert to_slp1("dharmakṣetre kurukṣetre") == "Darmakzetre kurukzetre"
    assert to_slp1("aiśvaryam auṣadham") == "ESvaryam OzaDam"
    # decomposed Unicode (NFD) gives the same result
    assert to_slp1(unicodedata.normalize("NFD", "kṛṣṇaḥ")) == "kfzRaH"
    # capital letters are not read as SLP1 (R would be ṇ)
    assert to_slp1("Rāmaḥ") == "rAmaH"


def test_slp1_positions():
    # "kh" (2 characters) becomes "K" (1) and "क" (1) becomes "ka" (2):
    # positions must still point to the original text
    s = "khaga"
    f = slp1_filter(s)
    assert f.get_string() == "Kaga"
    assert f.correct_position(1) == 2
    s = "कर"
    f = slp1_filter(s)
    assert f.get_string() == "kara"
    assert f.correct_position(2) == 1
    assert f.correct_position(4) == 2


def test_compound_hyphens():
    assert normalize("dharma-kṣetre") == normalize("dharmakṣetre")
    assert normalize("tat-puruṣa") == normalize("tatpuruṣa")
    assert normalize("manas-kāra") == normalize("manaskāra")
    # positions still point to the original text after removing the hyphen
    f = sanskrit_filters(slp1_filter("dharma-kṣetre"))
    assert f.get_string() == "Darmakzetre"
    assert f.correct_position(5) == 7


def test_doubled_consonants_after_r():
    assert normalize("dharmma") == normalize("dharma")
    assert normalize("kārtta") == normalize("kārta")
    assert normalize("varddhate") == normalize("vardhate")
    assert normalize("धर्म्म") == normalize("धर्म")


def test_nasals_and_anusvara():
    assert normalize("anta") == normalize("aṃta")
    assert normalize("saṅga") == normalize("saṃga")
    assert normalize("pañca") == normalize("paṃca")
    assert normalize("tam karoti") == normalize("taṃ karoti")
    assert normalize("vaṃśam̐") == normalize("vaṃśaṃ")
    # m before a vowel is not changed
    assert normalize("tam api") != normalize("taṃ api")


def test_visarga():
    assert normalize("devās tatra") == normalize("devāḥ tatra")
    assert normalize("punar") == normalize("punaḥ")
    assert normalize("yuyutsavaḥ |") == normalize("yuyutsavas |")
    # s and r inside a word are not changed
    assert normalize("sarva") == "sarva"
    # r before a vowel stays r, so that spacing doesn't matter (the tokenizer ignores spaces)
    assert normalize("buddhir ayuktasya").replace(" ", "") == normalize("buddhir-ayuktasya")
    assert normalize("punar api").replace(" ", "") == normalize("punarapi")
    # visarga written as the following sibilant
    assert normalize("niḥspṛhaḥ") == normalize("nisspṛhaḥ")
    assert normalize("duḥśāsana") == normalize("duśśāsana")


def test_b_and_v():
    # not by default: bala / vala are different words, and ब / व is an OCR confusion
    assert normalize("bala") != normalize("vala")
    rules_b_v = SANSKRIT_RULES + B_V_RULES
    assert sanskrit_filters(slp1_filter("bana"), rules_b_v).get_string() == sanskrit_filters(slp1_filter("vana"), rules_b_v).get_string()
    # bh is a different letter
    assert sanskrit_filters(slp1_filter("bhava"), rules_b_v).get_string() != sanskrit_filters(slp1_filter("vava"), rules_b_v).get_string()


def test_normalizer_rule_settings():
    # b = v as an option of the normalizer
    assert SanskritNormalizer().normalize_pre_token_comparison("ba") != SanskritNormalizer().normalize_pre_token_comparison("va")
    normalizer = SanskritNormalizer(normalize_b_v=True)
    assert normalizer.normalize_pre_token_comparison("ba") == normalizer.normalize_pre_token_comparison("va")
    # a subset of the rules, chosen by name
    without_doubling = [r for r in SANSKRIT_RULES if r[0] != "doubled consonant after r"]
    normalizer = SanskritNormalizer(rules=without_doubling)
    assert normalizer.normalize_pre_token_comparison("rmma") != normalizer.normalize_pre_token_comparison("rma")
    assert normalizer.normalize_pre_token_comparison("saṃ") == normalizer.normalize_pre_token_comparison("sañ")
