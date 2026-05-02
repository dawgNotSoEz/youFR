from __future__ import annotations

from ai_hall.claims.extractor import extract_claims
from ai_hall.correction.engine import generate_corrected_answer
from ai_hall.explanations.engine import explain_claim
from ai_hall.llm.clients.base import PassthroughClient
from ai_hall.pipeline.orchestrator import run_explain_pipeline
from ai_hall.pipeline.types import EvidenceSet, QueryRequest
from ai_hall.retrievers.hybrid import HybridRetriever, RetrievalConfig
from ai_hall.scoring.model import score_hallucination
from ai_hall.verifiers.ensemble import VerifierEnsemble
from ai_hall.verifiers.llm_grounded_judge import LLMGroundedJudgeVerifier
from ai_hall.verifiers.local_phi3 import LocalPhi3Verifier
from ai_hall.verifiers.memory_contradiction import VerifiedMemoryContradictionVerifier
from ai_hall.verifiers.nli import NLIVerifier


def run(query: str, *, answer_override: str | None = None, domain: str | None = None, team_id: str | None = None):
    llm = PassthroughClient()
    retriever = HybridRetriever(RetrievalConfig(max_evidence=5, local_corpus_dir="corpus"))
    ensemble = VerifierEnsemble(
        verifiers=[
            VerifiedMemoryContradictionVerifier(),
            NLIVerifier(),
            # Evidence-grounded judge (uses your existing MegaLLM client via services/llm_generator/client.py)
            LLMGroundedJudgeVerifier(llm),
            # Weak independent signal:
            LocalPhi3Verifier(),
        ]
    )

    def generate_fn(req: QueryRequest):
        return llm.generate(req)

    def extract_fn(answer_text: str):
        return extract_claims(answer_text)

    def retrieve_fn(claim):
        return retriever.retrieve(claim)

    def verify_fn(claim, evidence: EvidenceSet):
        vr = ensemble.verify(claim, evidence)
        return vr.outputs, vr

    def score_fn(claim, evidence, verification_result):
        return score_hallucination(claim, evidence, verification_result)

    def explain_fn(claim, evidence, verification_result, score):
        return explain_claim(claim, evidence, verification_result, score)

    def correct_fn(req, generation, analyses):
        return generate_corrected_answer(llm, req, generation, analyses)

    return run_explain_pipeline(
        QueryRequest(query=query, answer_override=answer_override, domain=domain, team_id=team_id),
        generate_fn=generate_fn,
        extract_claims_fn=extract_fn,
        retrieve_fn=retrieve_fn,
        verify_fn=verify_fn,
        score_fn=score_fn,
        explain_fn=explain_fn,
        correct_fn=correct_fn,
    )


if __name__ == "__main__":
    out = run("Who invented relativity?")
    print(out.model_dump_json(indent=2))

