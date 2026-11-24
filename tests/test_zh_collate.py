from pathlib import Path

from Pydurma.zh import collate_chinese, merge_chinese
from Pydurma.zh.normalizer_zh import ChineseNormalizer
from Pydurma.serializers.md import MdSerializer


def test_merge_chinese():
    witnesses = [
        "如是我聞：一時，佛在舍衛國，身ロ意業",
        "如是我聞。一時佛住舍衛國。身口意業",
        "如是我聞一時佛在舍衛國身口意業",
    ]
    assert merge_chinese(witnesses) == "如是我聞：一時，佛在舍衛國，身口意業"


def test_merge_chinese_two_witnesses():
    # 1 vs 1: the katakana look-alike ロ loses, whatever the order
    assert merge_chinese(["身ロ意業", "身口意業"]) == "身口意業"
    assert merge_chinese(["身口意業", "身ロ意業"]) == "身口意業"


def test_merge_chinese_options():
    # without the validity weigher, a 1 vs 1 tie keeps the first witness
    assert merge_chinese(["身ロ意業", "身口意業"], validity_weigher=False) == "身ロ意業"
    # with jp2t, the Japanese form 経 counts with 經
    witnesses = ["経", "經", "経"]
    assert merge_chinese(witnesses, normalizer=ChineseNormalizer(opencc_configs=["hk2t", "tw2t", "jp2t"]), validity_weigher=False) == "経"


def test_collate_chinese_with_serializer():
    witnesses = ["佛在舍衛國", "佛住舍衛國", "佛在舍衛國"]
    weighted = collate_chinese(witnesses)
    paths = [Path("a.txt"), Path("b.txt"), Path("c.txt")]
    md = MdSerializer(weighted, Path("."), "test", paths, {"a": "A", "b": "B", "c": "C"}).serialize_matrix()
    assert md.startswith("佛在[^1]舍衛國")
