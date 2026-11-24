"""
Convenience functions for the whole process on Sanskrit witnesses: tokenize,
align, weigh, and get the merged text.
"""
from pathlib import Path
from typing import List, Optional

from Pydurma.aligners.aligner import TokenMatrix
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.encoder import Encoder
from Pydurma.sa.normalizer_sa import SanskritNormalizer
from Pydurma.sa.tokenizer_sa import SanskritTokenizer
from Pydurma.serializers.plain_text import PlainTextSerializer
from Pydurma.weighers.matrix_weigher import TokenMatrixWeigher
from Pydurma.weighers.token_weigher_normalized_count import NormalizedTokenCountWeigher
from Pydurma.weighers.token_weigher_valid_sa import ValidSaTokenWeigher


def collate_sanskrit(
    witnesses: List[str],
    normalizer: Optional[SanskritNormalizer] = None,
    validity_weigher: bool = True,
) -> TokenMatrix:
    """
    Tokenizes and aligns the witnesses (strings, all in the same script), and weighs
    the readings with NormalizedTokenCountWeigher (majority vote) and, if
    validity_weigher is True, ValidSaTokenWeigher.

    Returns the weighted matrix (one column per witness, in the order given), which
    can be passed to any serializer (MdSerializer, CSVSerializer, etc.).
    """
    normalizer = normalizer if normalizer is not None else SanskritNormalizer()
    tokenizer = SanskritTokenizer(Encoder(), normalizer)
    token_strings, token_lists = [], []
    for witness in witnesses:
        token_string, token_list = tokenizer.tokenize(witness)
        token_strings.append(token_string)
        token_lists.append(token_list)
    matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)
    matrix_weigher = TokenMatrixWeigher()
    matrix_weigher.add_weigher(NormalizedTokenCountWeigher(normalizer), 1)
    if validity_weigher:
        matrix_weigher.add_weigher(ValidSaTokenWeigher(normalizer), 1)
    return matrix_weigher.get_weight_matrix(matrix)


def merge_sanskrit(witnesses: List[str], **kwargs) -> str:
    """
    Returns the merged text of the witnesses: the best reading at each point (see
    collate_sanskrit for the arguments).
    """
    weighted_matrix = collate_sanskrit(witnesses, **kwargs)
    return PlainTextSerializer(weighted_matrix, Path("."), "merged").serialize_matrix()
