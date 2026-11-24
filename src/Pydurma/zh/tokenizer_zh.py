import re
from typing import Tuple

from Pydurma.normalizer import Normalizer
from Pydurma.tokenizer import Tokenizer, TokenList
from Pydurma.encoder import Encoder


class ChineseTokenizer(Tokenizer):
    """
    Tokenizer for Chinese: one token per character, no word segmentation.

    Punctuation is its own token (like the shad in the Tibetan tokenizer), with the
    whitespace that follows it, so that witnesses that differ only in punctuation
    get their own row in the alignment and the punctuation can be voted on
    separately from the characters. Whitespace alone (e.g. line breaks) is kept in
    the token list but ignored in the diff.

    Non-Chinese letters and digits are also one token per character.
    """

    # one word character, or a run of non-word characters
    token_pattern = re.compile(r"[^\W_]|[\W_]+")

    def __init__(self, encoder: Encoder, normalizer: Normalizer):
        super().__init__(encoder, normalizer)

    def tokenize(self, arg) -> Tuple[str, TokenList]:
        tokens = []
        tokenstr = ""
        string, correct_position = self.get_input(arg)
        for m in ChineseTokenizer.token_pattern.finditer(string):
            token_s = self.normalizer.normalize_always(m.group(0))
            start = correct_position(m.start())
            end = correct_position(m.end())
            token_s_for_diff = self.normalizer.normalize_pre_token_diff(token_s)
            if token_s_for_diff == "":
                # whitespace only: kept in the token list but ignored in the diff
                tokens.append((start, end, 0, token_s))
                continue
            code_str, code_str_len = self.encoder.encode_str(token_s_for_diff)
            tokenstr += code_str
            tokens.append((start, end, code_str_len, token_s))
        return tokenstr, tokens
