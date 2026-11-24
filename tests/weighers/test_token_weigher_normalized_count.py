from Pydurma.gen.normalizer_gen import GenericNormalizer
from Pydurma.weighers.token_weigher_count import TokenCountWeigher
from Pydurma.weighers.token_weigher_normalized_count import NormalizedTokenCountWeigher


def test_counts_normalized_forms_together():
    # GenericNormalizer lowercases and removes final spaces: "The" and "the " are the same reading
    column = [(0, 3, 1, "The"), (0, 4, 1, "the "), (0, 1, 1, "a")]
    assert TokenCountWeigher().weigh(column) == [33, 33, 33]
    assert NormalizedTokenCountWeigher(GenericNormalizer()).weigh(column) == [66, 66, 33]


def test_gaps():
    column = [(0, 3, 1, "the"), None, None, (0, 0, 1, "")]
    assert NormalizedTokenCountWeigher(GenericNormalizer()).weigh(column) == [25, 75, 75, 75]


def test_unanimous():
    column = [(0, 3, 1, "the"), (0, 3, 1, "THE")]
    assert NormalizedTokenCountWeigher(GenericNormalizer()).weigh(column) == [100, 100]
