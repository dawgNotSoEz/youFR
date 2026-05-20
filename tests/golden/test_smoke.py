import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_hall.app import run


def mock_wikipedia_search(query, results=5):
    if "relativity" in query.lower() or "einstein" in query.lower():
        return ["Albert Einstein"]
    return []


def mock_wikipedia_summary(title, sentences=4, auto_suggest=False):
    if "einstein" in title.lower():
        return "Albert Einstein formulated the theory of special relativity in 1905 and general relativity in 1915. He won the Nobel Prize in Physics in 1921."
    return "This is a mock wikipedia page summary."


class MockPage:
    def __init__(self, title):
        self.title = title
        self.content = "Albert Einstein formulated the theory of special relativity in 1905 and general relativity in 1915.\nHe won the Nobel Prize in Physics in 1921 for the photoelectric effect, not for relativity."


def mock_wikipedia_page(title, auto_suggest=False, preload=False):
    return MockPage(title)


@patch("wikipedia.search", side_effect=mock_wikipedia_search)
@patch("wikipedia.summary", side_effect=mock_wikipedia_summary)
@patch("wikipedia.page", side_effect=mock_wikipedia_page)
def test_pipeline_smoke(mock_page, mock_summary, mock_search):
    out = run("Who invented relativity?")
    assert out.generation.answer_text
    assert isinstance(out.claims, list)
    assert out.summary.reason
    assert out.summary.hard_gate_passed is True


