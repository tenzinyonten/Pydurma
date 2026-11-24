from collections import Counter
from typing import List

from Pydurma.normalizer import Normalizer
from Pydurma.tokenizer import Token
from Pydurma.weighers.token_weigher import TokenWeigher


class NormalizedTokenCountWeigher(TokenWeigher):
    """
    Like TokenCountWeigher (majority vote), but tokens are counted by their
    normalized form, so that readings that only differ in spelling or punctuation
    count as the same reading.

    TokenCountWeigher compares the token text directly, so for instance in Chinese
    衆 / 眾 (variant characters) or 聞： / 聞。 (punctuation) would split the vote.
    With the language's normalizer, they are counted together.

    The normalized form is given by normalizer.normalize_pre_token_comparison()
    applied to the token text (token[3]). Gaps count as the empty string.

    The weight of a token is the percentage of witnesses that have the same
    normalized reading, as an integer between 0 and 100.
    """

    def __init__(self, normalizer: Normalizer, relative: bool = False):
        super().__init__(relative)
        self.normalizer = normalizer

    def comparison_form(self, token: Token) -> str:
        if token is None or token[3] is None:
            return ""
        return self.normalizer.normalize_pre_token_comparison(token[3])

    def weigh(self, column: List[Token]) -> List[int]:
        forms = [self.comparison_form(token) for token in column]
        counts = Counter(forms)
        total = len(column)
        return [int(counts[form] / total * 100) for form in forms]
