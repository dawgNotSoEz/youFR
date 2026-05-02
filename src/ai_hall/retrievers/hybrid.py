from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from ai_hall.pipeline.types import Claim, EvidenceItem, EvidenceSet
from ai_hall.retrievers.bm25 import BM25Index
from ai_hall.retrievers.corpus import LocalTextCorpus
from ai_hall.utils.hashing import stable_hash


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RetrievalConfig:
    max_evidence: int = 5
    local_corpus_dir: str | None = None
    bm25_top_k: int = 5


class WikiRetrieverAdapter:
    """
    Adapter over the existing `services/retriever/wiki_retriever.py` implementation.
    This is a v1 evidence engine: it returns a few paragraphs + titles as sources.
    Next step: replace with hybrid BM25+dense+rerank over a local corpus.
    """

    def __init__(self, cfg: RetrievalConfig | None = None):
        self.cfg = cfg or RetrievalConfig()

    def retrieve(self, claim: Claim) -> EvidenceSet:
        from services.retriever.wiki_retriever import get_evidence

        payload = get_evidence(claim.text) or {}
        evidence_text = str(payload.get("evidence", "") or "")
        sources = payload.get("sources", []) if isinstance(payload.get("sources", []), list) else []

        items: list[EvidenceItem] = []
        # Split rough paragraphs; treat each as an evidence item.
        paragraphs = [p.strip() for p in evidence_text.split("  ") if p.strip()]
        if not paragraphs:
            paragraphs = [evidence_text.strip()] if evidence_text.strip() else []

        for idx, para in enumerate(paragraphs[: self.cfg.max_evidence]):
            src = sources[idx] if idx < len(sources) else (sources[0] if sources else None)
            evid_id = stable_hash({"claim_id": claim.claim_id, "idx": idx, "snippet": para[:200]})
            items.append(
                EvidenceItem(
                    evidence_id=evid_id,
                    source_type="wiki",
                    uri=str(src) if src else None,
                    title=str(src) if src else None,
                    snippet=para,
                    retrieved_at=_utc_iso(),
                    score=0.5,
                    credibility=0.6,
                )
            )

        return EvidenceSet(claim_id=claim.claim_id, items=items)


class HybridRetriever:
    """
    v1 hybrid retriever:
    - If `local_corpus_dir` exists: BM25 over local *.txt docs, returns best doc snippets.
    - Otherwise: fall back to the existing Wikipedia retriever adapter.
    """

    def __init__(self, cfg: RetrievalConfig | None = None):
        self.cfg = cfg or RetrievalConfig()
        self._wiki = WikiRetrieverAdapter(self.cfg)
        self._bm25 = None
        if self.cfg.local_corpus_dir:
            corpus = LocalTextCorpus(self.cfg.local_corpus_dir).load()
            self._bm25 = BM25Index(corpus.docs) if corpus.docs else None

    def retrieve(self, claim: Claim) -> EvidenceSet:
        if self._bm25 is None:
            return self._wiki.retrieve(claim)

        hits = self._bm25.search(claim.text, top_k=self.cfg.bm25_top_k)
        items: list[EvidenceItem] = []
        for idx, h in enumerate(hits[: self.cfg.max_evidence]):
            snippet = (h.doc.text or "").strip().replace("\n", " ")
            snippet = snippet[:800]
            evid_id = stable_hash({"claim_id": claim.claim_id, "doc_id": h.doc.doc_id, "idx": idx})
            items.append(
                EvidenceItem(
                    evidence_id=evid_id,
                    source_type="local",
                    uri=h.doc.uri,
                    title=h.doc.title,
                    snippet=snippet,
                    retrieved_at=_utc_iso(),
                    score=float(h.score),
                    credibility=0.7,
                    metadata={"doc_id": h.doc.doc_id},
                )
            )

        # If BM25 returns nothing, backstop with wiki so the system can still work.
        if not items:
            return self._wiki.retrieve(claim)

        return EvidenceSet(claim_id=claim.claim_id, items=items)

