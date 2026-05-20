from __future__ import annotations

import re
from dataclasses import dataclass

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

from ai_hall.retrievers.corpus import CorpusDocument


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9][a-zA-Z0-9'-]+", (text or "").lower())


@dataclass
class BM25Hit:
    doc: CorpusDocument
    score: float


class BM25Index:
    def __init__(self, docs: list[CorpusDocument]):
        self.docs = docs
        if BM25Okapi is not None and docs:
            self._bm25 = BM25Okapi([_tokenize(d.text) for d in docs])
        else:
            self._bm25 = None

    def search(self, query: str, *, top_k: int = 10) -> list[BM25Hit]:
        if not self._bm25 or not self.docs:
            return []
        q = _tokenize(query)
        scores = self._bm25.get_scores(q)
        ranked = sorted(range(len(self.docs)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [BM25Hit(doc=self.docs[i], score=float(scores[i])) for i in ranked if scores[i] > 0]


