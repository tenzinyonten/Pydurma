"""
Convenience functions for the whole process on Chinese witnesses: tokenize,
align, weigh, and get the merged text.
"""
from pathlib import Path
from typing import List, Optional

from Pydurma.aligners.aligner import TokenMatrix
from Pydurma.aligners.fdmp import FDMPaligner
from Pydurma.encoder import Encoder
from Pydurma.zh.normalizer_zh import ChineseNormalizer
from Pydurma.zh.tokenizer_zh import ChineseTokenizer
from Pydurma.serializers.plain_text import PlainTextSerializer
from Pydurma.weighers.matrix_weigher import TokenMatrixWeigher
from Pydurma.weighers.token_weigher_normalized_count import NormalizedTokenCountWeigher
from Pydurma.weighers.token_weigher_valid_zh import ValidZhTokenWeigher


def collate_chinese(
    witnesses: List[str],
    normalizer: Optional[ChineseNormalizer] = None,
    validity_weigher: bool = True,
    rare_characters: bool = True,
) -> TokenMatrix:
    """
    Tokenizes and aligns the witnesses (strings), and weighs the readings with
    NormalizedTokenCountWeigher (majority vote) and, if validity_weigher is True,
    ValidZhTokenWeigher: foreign characters (e.g. katakana look-alikes), and if
    rare_characters is True, characters that appear only once in all the witnesses.

    Returns the weighted matrix (one column per witness, in the order given), which
    can be passed to any serializer (MdSerializer, CSVSerializer, etc.).
    """
    normalizer = normalizer if normalizer is not None else ChineseNormalizer()
    tokenizer = ChineseTokenizer(Encoder(), normalizer)
    token_strings, token_lists = [], []
    for witness in witnesses:
        token_string, token_list = tokenizer.tokenize(witness)
        token_strings.append(token_string)
        token_lists.append(token_list)
    matrix = FDMPaligner().get_alignment_matrix(token_strings, token_lists)
    matrix_weigher = TokenMatrixWeigher()
    matrix_weigher.add_weigher(NormalizedTokenCountWeigher(normalizer), 1)
    if validity_weigher:
        if rare_characters:
            weigher = ValidZhTokenWeigher.from_texts(witnesses, normalizer)
        else:
            weigher = ValidZhTokenWeigher(normalizer)
        matrix_weigher.add_weigher(weigher, 1)
    return matrix_weigher.get_weight_matrix(matrix)


def merge_chinese(witnesses: List[str], **kwargs) -> str:
    """
    Returns the merged text of the witnesses: the best reading at each point (see
    collate_chinese for the arguments).
    """
    weighted_matrix = collate_chinese(witnesses, **kwargs)
    return PlainTextSerializer(weighted_matrix, Path("."), "merged").serialize_matrix()
