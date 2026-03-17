import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.llm_generator.generate import generate_answer, get_last_call_info
from services.claim_extractor.extractor import extract_claims_with_metadata
from services.verifier.groq_verifier import verify_claim, verify_claim_llm_only
from services.aggregator.aggregate import aggregate_results
try:
    from services.retriever.wiki_retriever import get_evidence
except Exception:
    from archive.services.retriever.wiki_retriever import get_evidence
from services.classifier.failure_classifier import classify_failure
from services.explainer.explain import generate_explanation
from services.verifier.local_verifier import verify_local


def run_pipeline(query):

    answer = generate_answer(query)
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

    results = []
    fusion_input = []

    for claim in claims:
        llm_result = verify_claim_llm_only(claim)
        evidence = get_evidence(claim)
        evidence_result = verify_claim(claim, evidence=evidence)
        local_result = verify_local(claim)

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
        }
        fusion_input.append(fusion_claim)

        results.append(
            {
                "claim": claim,
                "llm_verdict": llm_result,
                "evidence_verdict": evidence_result,
                "evidence": evidence,
            }
        )

    aggregated = aggregate_results(fusion_input)

    for item in aggregated["fused_results"]:
        print("\n[FUSION DEBUG] claim:", item["claim"])
        print("[FUSION DEBUG] llm status:", item["llm"].get("status", "UNCERTAIN"))
        print("[FUSION DEBUG] evidence status:", item["evidence"].get("status", "UNCERTAIN"))
        print("[FUSION DEBUG] fused result:", item["fused"])

    hallucination = aggregated["hallucination"]
    reason = aggregated["reason"]

    fused_statuses = [item["fused"].get("final_status", "UNCERTAIN") for item in aggregated["fused_results"]]
    fused_for_classifier = [{"status": status} for status in fused_statuses]

    if fused_statuses and not hallucination and all(status == "TRUE" for status in fused_statuses):
        reason = "All extracted factual claims verified as true after fusion"

    error_type = classify_failure(fused_for_classifier)
    explanation = generate_explanation(error_type)

    final_summary = {
        "hallucination": hallucination,
        "reason": reason,
        "notes": notes,
        "error_type": error_type,
        "explanation": explanation,
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
    }

    return output


if __name__ == "__main__":

    query = "Who invented relativity?"

    pipeline_output = run_pipeline(query)
    results = pipeline_output["results"]

    for r in results:
        print("\n--- CLAIM ---")
        print(r["claim"])

        print("\nLLM VERDICT:")
        print(r["llm_verdict"])

        print("\nEVIDENCE VERDICT:")
        print(r["evidence_verdict"])

        print("\nEVIDENCE:")
        print(r["evidence"])

    print("\n--- ERROR TYPE ---")
    print(pipeline_output["summary"]["error_type"])

    print("\n--- EXPLANATION ---")
    print(pipeline_output["summary"]["explanation"])

    print("\nFinal Output:")
    print(pipeline_output["summary"])