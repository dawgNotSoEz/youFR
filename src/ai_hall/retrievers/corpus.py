from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class CorpusDocument:
    doc_id: str
    title: str
    text: str
    uri: str | None = None


class LocalTextCorpus:
    """
    Minimal local corpus loader.

    Expected layout:
      corpus_dir/
        *.txt  (one document per file)
    """

    def __init__(self, corpus_dir: str | Path):
        self.corpus_dir = Path(corpus_dir)
        self.docs: list[CorpusDocument] = []

    def load(self) -> "LocalTextCorpus":
        self.docs = []
        if not self.corpus_dir.exists():
            return self
        for p in sorted(self.corpus_dir.glob("*.txt")):
            text = p.read_text(encoding="utf-8", errors="ignore")
            self.docs.append(CorpusDocument(doc_id=p.stem, title=p.stem, text=text, uri=str(p)))
        return self

