import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_hall.app import run


def test_pipeline_smoke():
    out = run("Who invented relativity?")
    assert out.generation.answer_text
    assert isinstance(out.claims, list)
    assert out.summary.reason

