from __future__ import annotations

from ai_hall.llm.clients.base import LLMClient
from ai_hall.pipeline.types import ClaimAnalysis, LLMGeneration, QueryRequest


def generate_corrected_answer(
    llm: LLMClient,
    request: QueryRequest,
    generation: LLMGeneration,
    analyses: list[ClaimAnalysis],
) -> str | None:
    failing = [a for a in analyses if a.score.p_hallucination >= 0.7]
    if not failing:
        return None

    evidence_map = {}
    failed_claims = []
    for a in failing[:8]:
        failed_claims.append(a.claim.text)
        ev = a.evidence.items[0].snippet[:300] if a.evidence.items else "No evidence retrieved."
        evidence_map[a.claim.text] = ev

    prompt = f"""
You are a factual correction system.

Rules:
- Fix incorrect facts ONLY for the failed claims listed.
- Keep all correct content unchanged.
- Use ONLY the evidence snippets provided. If evidence is insufficient, rewrite conservatively and mark uncertainty.
- Return ONLY corrected answer text (no explanation).

User query:
{request.query}

Original answer:
{generation.answer_text}

Failed claims:
{failed_claims}

Evidence snippets by claim:
{evidence_map}
""".strip()

    return llm.judge(prompt).strip() or None

