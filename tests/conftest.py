import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from backend.knowledge_base import load_knowledge_base


@pytest.fixture
def kb():
    return load_knowledge_base()
