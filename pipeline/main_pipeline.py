import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.llm_generator.generate import generate_answer, get_last_call_info
from services.claim_extractor.extractor import extract_claims_with_metadata
from services.verifier.groq_verifier import verify_claim, verify_claim_llm_only
from services.verifier.local_verifier import verify_locally
from services.verifier.memory_consistency import (
    append_verified_claims,
    check_memory_contradiction,
    load_verified_facts,
    save_verified_facts,
)
from services.corrector.correct import correct_answer
from services.aggregator.aggregate import aggregate_results, fuse
from services.memory.memory_store import memory_db, store_verified_claims
try:
    from services.retriever.wiki_retriever import get_evidence
except Exception:
    from archive.services.retriever.wiki_retriever import get_evidence
from services.classifier.failure_classifier import classify_failure
from services.explainer.explain import generate_explanation
from services.verifier.evidence_filter import is_evidence_relevant
from services.embeddings.embedding_verifier import embedding_score

MAX_ATTEMPTS = 2

def _evaluate_answer(query: str, answer: str, verified_facts: list[dict]) -> dict:

    llm_info = get_last_call_info()

    print("LLM Call Info:", llm_info)
    usage = llm_info.get("usage") if isinstance(llm_info, dict) else None
    if isinstance(usage, dict):
        total_tokens = usage.get("total_tokens")
        if total_tokens is not None:
            print(f"LLM Tokens Used: {total_tokens}")

    print("AI Answer:\n", answer)

    claim_bundle = extract_claims_with_metadata(answer)
    claims = claim_bundle["claims"]
    notes = claim_bundle["notes"]

    print("\nExtracted Claims:\n", claims)

    if not claims:
        final_summary = {
            "hallucination": True,
            "reason": "No claims extracted; hard gating blocked output",
            "notes": notes,
            "error_type": "INSUFFICIENT_EVIDENCE",
            "explanation": "No claims were extracted for verification, so the answer cannot be returned.",
            "final_status": "FALSE",
            "hard_gate_passed": False,
            "metrics": {
                "total_claims": 0,
                "false_count": 0,
                "uncertain_count": 0,
                "uncertain_ratio": 0.0,
            },
        }
        return {
            "results": [],
            "summary": final_summary,
            "draft_answer": answer,
            "all_claims_true": False,
            "failed_claims": ["<none>"],
            "evidence_map": {"<none>": "No claims extracted"},
        }

    results = []
    fusion_input = []

    for claim in claims:
        memory_result = check_memory_contradiction(claim, verified_facts)

        if memory_result:
            llm_result = {
                "claim": claim,
                "status": "FALSE",
                "confidence": 1.0,
                "reason": memory_result["reason"],
            }
            evidence_result = {
                "claim": claim,
                "status": "FALSE",
                "confidence": 1.0,
                "reason": memory_result["reason"],
            }
            local_result = {
                "claim": claim,
                "status": "FALSE",
                "confidence": 1.0,
                "reason": memory_result["reason"],
            }
            evidence = ""
            evidence_sources = []
            embed_result = {
                "score": 0.0,
                "reason": "Memory contradiction",
            }
        else:
            llm_result = verify_claim_llm_only(claim)
            local_result = verify_locally(claim)
            evidence_payload = get_evidence(claim)

            if isinstance(evidence_payload, dict):
                evidence = str(evidence_payload.get("evidence", ""))
                evidence_sources = evidence_payload.get("sources", [])
            else:
                evidence = str(evidence_payload or "")
                evidence_sources = []

            if not is_evidence_relevant(claim, evidence):
                evidence_result = {
                    "claim": claim,
                    "status": "UNCERTAIN",
                    "confidence": 0.0,
                    "reason": "Evidence filtered as irrelevant",
                }
            else:
                evidence_result = verify_claim(claim, evidence=evidence)

            embed_result = embedding_score(claim, evidence)

        fused_result = fuse(
            {
                "status": llm_result.get("status", "UNCERTAIN"),
                "confidence": llm_result.get("confidence", 0.0),
            },
            {
                "status": evidence_result.get("status", "UNCERTAIN"),
                "confidence": evidence_result.get("confidence", 0.0),
            },
            embed_result,
            {
                "status": local_result.get("status", "UNCERTAIN"),
                "confidence": local_result.get("confidence", 0.0),
            },
        )

        print("\n--- CLAIM ---")
        print(claim)

        print("\nLLM VERDICT:")
        print(llm_result)

        print("\nEVIDENCE VERDICT:")
        print(evidence_result)

        print("\nLOCAL VERIFIER:")
        print(local_result)

        print("\nEVIDENCE:")
        print(evidence[:300])

        print("\nEMBEDDING SCORE:")
        print(embed_result)

        print("\nFUSED RESULT:")
        print(fused_result)

        fusion_claim = {
            "claim": claim,
            "llm": {
                "status": llm_result.get("status", "UNCERTAIN"),
                "confidence": llm_result.get("confidence", 0.0),
            },
            "evidence": {
                "status": evidence_result.get("status", "UNCERTAIN"),
                "confidence": evidence_result.get("confidence", 0.0),
            },
            "local": {
                "status": local_result.get("status", "UNCERTAIN"),
                "confidence": local_result.get("confidence", 0.0),
            },
            "embedding": embed_result,
        }
        fusion_input.append(fusion_claim)

        results.append(
            {
                "claim": claim,
                "llm_verdict": llm_result,
                "evidence_verdict": evidence_result,
                "local": local_result,
                "embedding": embed_result,
                "evidence": evidence,
                "sources": evidence_sources,
                "memory_check": memory_result,
                "fused_result": fused_result,
            }
        )

    aggregated = aggregate_results(fusion_input)

    for item in aggregated["fused_results"]:
        print("\n[FUSION DEBUG] claim:", item["claim"])
        print("[FUSION DEBUG] llm status:", item["llm"].get("status", "UNCERTAIN"))
        print("[FUSION DEBUG] evidence status:", item["evidence"].get("status", "UNCERTAIN"))
        if item.get("local"):
            print("[FUSION DEBUG] local status:", item["local"].get("status", "UNCERTAIN"))
        print("[FUSION DEBUG] embedding score:", item.get("embedding", {}).get("score"))
        print("[FUSION DEBUG] fused result:", item["fused"])

    hallucination = aggregated["hallucination"]
    reason = aggregated["reason"]

    fused_statuses = [item["fused"].get("final_status", "UNCERTAIN") for item in aggregated["fused_results"]]
    fused_for_classifier = [{"status": status} for status in fused_statuses]
    all_claims_true = bool(fused_statuses) and all(status == "TRUE" for status in fused_statuses)
    hard_gate_passed = all_claims_true and not hallucination

    if hard_gate_passed:
        reason = "All extracted factual claims verified as true after fusion"
    elif reason == "No hallucination after fusion":
        reason = "Hard gate blocked output because at least one claim was not TRUE"

    error_type = classify_failure(fused_for_classifier)
    explanation = generate_explanation(error_type)

    final_summary = {
        "hallucination": hallucination,
        "reason": reason,
        "notes": notes,
        "error_type": error_type,
        "explanation": explanation,
        "final_status": "TRUE" if hard_gate_passed else "FALSE",
        "hard_gate_passed": hard_gate_passed,
        "metrics": {
            "total_claims": aggregated["total_claims"],
            "false_count": aggregated["false_count"],
            "uncertain_count": aggregated["uncertain_count"],
            "uncertain_ratio": aggregated["uncertain_ratio"],
        },
    }

    output = {
        "results": results,
        "summary": final_summary,
        "draft_answer": answer,
    }

    failed_claims = []
    evidence_map = {}
    for result_item in results:
        final_status = result_item.get("fused_result", {}).get("final_status", "UNCERTAIN")
        if final_status == "TRUE":
            continue

        claim_text = result_item.get("claim", "")
        if claim_text:
            failed_claims.append(claim_text)
            evidence_text = str(result_item.get("evidence", "") or "").strip()
            evidence_map[claim_text] = (
                evidence_text[:300]
                if evidence_text
                else result_item.get("fused_result", {}).get("reason", "No evidence available")
            )

    return {
        **output,
        "all_claims_true": hard_gate_passed,
        "failed_claims": failed_claims,
        "evidence_map": evidence_map,
    }


def run_pipeline(query, max_attempts: int = MAX_ATTEMPTS):
    verified_facts = load_verified_facts()
    answer = generate_answer(query)
    original_answer = answer
    attempts = 0
    last_evaluation = None
    correction_count = 0

    while attempts < max_attempts:
        evaluation = _evaluate_answer(query=query, answer=answer, verified_facts=verified_facts)
        last_evaluation = evaluation

        evaluated_claims = [item.get("claim", "") for item in evaluation.get("results", []) if item.get("claim")]
        fused_results = [
            {"final_status": item.get("fused_result", {}).get("final_status", "UNCERTAIN")}
            for item in evaluation.get("results", [])
        ]
        store_verified_claims(evaluated_claims, fused_results)

        print("\n[MEMORY]")
        print(memory_db[-5:])

        failed_claims = evaluation.get("failed_claims", [])
        print("\n[CORRECTION LOOP]")
        print("Attempt:", attempts)
        print("Failed claims:", failed_claims)

        if evaluation.get("all_claims_true"):
            approved_claims = [item.get("claim", "") for item in evaluation.get("results", []) if item.get("claim")]
            verified_facts = append_verified_claims(verified_facts, approved_claims, source_query=query)
            save_verified_facts(verified_facts)

            return {
                "attempts_used": attempts,
                "max_attempts": max_attempts,
                "correction_count": correction_count,
                "original_answer": original_answer,
                "final_answer": answer,
                "last_corrected_answer": answer,
                "results": evaluation["results"],
                "summary": evaluation["summary"],
            }

        answer = correct_answer(
            query=query,
            answer=answer,
            failed_claims=failed_claims,
            evidence_map=evaluation.get("evidence_map", {}),
        )
        correction_count += 1
        attempts += 1

    blocked_summary = dict((last_evaluation or {}).get("summary", {}))
    blocked_summary["reason"] = (
        f"Hard gate blocked output after {max_attempts} attempts; no fully TRUE verification achieved"
    )
    blocked_summary["final_status"] = "FALSE"
    blocked_summary["hard_gate_passed"] = False

    final_statuses = [
        item.get("fused_result", {}).get("final_status", "UNCERTAIN")
        for item in (last_evaluation or {}).get("results", [])
    ]
    if "UNCERTAIN" in final_statuses:
        print("⚠️ returning best corrected answer (safe fallback)")

    safe_fallback_answer = (answer or "").strip() or (original_answer or "").strip()

    return {
        "attempts_used": attempts,
        "max_attempts": max_attempts,
        "correction_count": correction_count,
        "original_answer": original_answer,
        "final_answer": safe_fallback_answer,
        "last_corrected_answer": safe_fallback_answer,
        "results": (last_evaluation or {}).get("results", []),
        "summary": blocked_summary,
    }


if __name__ == "__main__":

    query = "Who invented relativity?"

    pipeline_output = run_pipeline(query, max_attempts=MAX_ATTEMPTS)
    results = pipeline_output["results"]

    for r in results:
        print("\nSOURCES:")
        print(r.get("sources", []))

    print("\n--- ERROR TYPE ---")
    print(pipeline_output["summary"]["error_type"])

    print("\n--- EXPLANATION ---")
    print(pipeline_output["summary"]["explanation"])

    print("\nFinal Output:")
    print(pipeline_output["summary"])
    print("\nFinal Answer Returned:")
    print(pipeline_output.get("final_answer"))