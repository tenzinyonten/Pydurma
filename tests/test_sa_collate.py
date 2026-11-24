from pathlib import Path

from Pydurma.sa import collate_sanskrit, merge_sanskrit
from Pydurma.sa.normalizer_sa import SanskritNormalizer
from Pydurma.serializers.md import MdSerializer


def test_merge_sanskrit():
    witnesses = [
        "dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |",
        "dharmmakṣetre kurukṣetre samāgatā yuyutsavaḥ |",
        "dhkarmakṣetre kurukṣetre samavetā yuyutsavas",
    ]
    assert merge_sanskrit(witnesses) == "dharmakṣetre kurukṣetre samavetā yuyutsavaḥ |"


def test_merge_sanskrit_two_witnesses_devanagari():
    # 1 vs 1: the validity weigher makes the well-formed reading win
    assert merge_sanskrit(["ध्कर्मक्षेत्रे समवेता", "धर्मक्षेत्रे समवेता"]) == "धर्मक्षेत्रे समवेता"


def test_merge_sanskrit_options():
    # b = v off by default: bala (2) wins over vala (1); with b = v, all three count
    # as one reading and the first spelling is written
    witnesses = ["vala", "bala", "bala"]
    assert merge_sanskrit(witnesses) == "bala"
    assert merge_sanskrit(witnesses, normalizer=SanskritNormalizer(normalize_b_v=True)) == "vala"


def test_collate_sanskrit_with_serializer():
    witnesses = ["dharmakṣetre", "dharmmakṣetre", "dharmakṣetre"]
    weighted = collate_sanskrit(witnesses)
    paths = [Path("a.txt"), Path("b.txt"), Path("c.txt")]
    md = MdSerializer(weighted, Path("."), "test", paths, {"a": "A", "b": "B", "c": "C"}).serialize_matrix()
    assert md.startswith("dharma[^1]kṣetre")
