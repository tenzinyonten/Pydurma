import subprocess
import sys

import pytest

# each import is tested in a new Python process, as the import order matters for
# circular imports (Pydurma.sa exports collate.py, which imports the weighers)
IMPORTS = [
    "from Pydurma.weighers.token_weigher_valid_sa import ValidSaTokenWeigher",
    "from Pydurma.sa.normalizer_sa import SanskritNormalizer",
    "from Pydurma.sa.tokenizer_sa import SanskritTokenizer",
    "from Pydurma.sa import merge_sanskrit, collate_sanskrit",
    "from Pydurma.sa.collate import collate_sanskrit",
]


@pytest.mark.parametrize("statement", IMPORTS)
def test_import_in_new_process(statement):
    result = subprocess.run([sys.executable, "-c", statement], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
