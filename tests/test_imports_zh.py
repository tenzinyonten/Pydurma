import subprocess
import sys

import pytest

# each import is tested in a new Python process, as the import order matters for
# circular imports (Pydurma.zh exports collate.py, which imports the weighers)
IMPORTS = [
    "from Pydurma.weighers.token_weigher_valid_zh import ValidZhTokenWeigher",
    "from Pydurma.zh.normalizer_zh import ChineseNormalizer",
    "from Pydurma.zh.tokenizer_zh import ChineseTokenizer",
    "from Pydurma.zh import merge_chinese, collate_chinese",
    "from Pydurma.zh.collate import collate_chinese",
]


@pytest.mark.parametrize("statement", IMPORTS)
def test_import_in_new_process(statement):
    result = subprocess.run([sys.executable, "-c", statement], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
