import re
from typing import Tuple

from Pydurma.tokenizer import Tokenizer, TokenList
from Pydurma.encoder import Encoder
from Pydurma.input_filters.input_filter import InputFilter
from Pydurma.sa.normalizer_sa import SanskritNormalizer
from Pydurma.sa.filters_sa import CONSONANTS, VOWELS


class SanskritTokenizer(Tokenizer):
    """
    Tokenizer for Sanskrit: one token per akṣara (syllable).

    An akṣara is any number of consonants followed by a vowel (and an optional
    anusvāra / visarga / candrabindu). Consonants at the end of the text with no
    vowel after them form their own token.

    Spaces are ignored when splitting, so a word-final consonant joins the next
    word's first vowel: "tad api" and "tadapi" both give ta | da | pi. This matters
    because witnesses often split words differently.

    Input can be Devanagari or IAST. Before splitting, the whole text is converted to
    SLP1 and normalized with the rules in filters_sa.py (see SanskritNormalizer for
    the settings); the alignment compares this normalized form. The token text
    (token[3]) is the original text of the akṣara, like in the Tibetan tokenizer, and
    token positions refer to the original string.
    """

    # consonants (spaces allowed between them) + vowel, then anything that is not a letter
    token_pattern = re.compile(
        "(?:[" + CONSONANTS + r"]\s*)*[" + VOWELS + "][^" + CONSONANTS + VOWELS + "]*"
        + "|(?:[" + CONSONANTS + r"]\s*)+[^" + CONSONANTS + VOWELS + "]*"
        + "|[^" + CONSONANTS + VOWELS + "]+"
    )

    def __init__(self, encoder: Encoder, normalizer: SanskritNormalizer):
        super().__init__(encoder, normalizer)

    def tokenize(self, arg) -> Tuple[str, TokenList]:
        # the text as given (after the caller's own input filters, if any), and the
        # function to get positions in the original string from positions in it
        if isinstance(arg, InputFilter):
            text = arg.get_string()
            to_original = arg.correct_position
        else:
            text = arg
            to_original = lambda x: x
        # the normalized SLP1 version of the text, used for splitting and comparison
        normalized, to_text = self.get_input(self.normalizer.to_normalized_slp1(text))
        tokens = []
        tokenstr = ""
        for m in SanskritTokenizer.token_pattern.finditer(normalized):
            text_start = to_text(m.start())
            text_end = to_text(m.end())
            token_s = self.normalizer.normalize_always(text[text_start:text_end])
            start = to_original(text_start)
            end = to_original(text_end)
            token_s_for_diff = self.normalizer.normalize_pre_token_diff(m.group(0))
            if token_s_for_diff == "":
                # no letters (daṇḍas, punctuation): kept but ignored in the diff
                tokens.append((start, end, 0, token_s))
                continue
            code_str, code_str_len = self.encoder.encode_str(token_s_for_diff)
            tokenstr += code_str
            tokens.append((start, end, code_str_len, token_s))
        return tokenstr, tokens
