import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.llm_generator.generate import generate_answer, get_last_call_info
from services.claim_extractor.extractor import extract_claims_with_metadata
from services.verifier.groq_verifier import verify_claim
from services.detector.hallucination import detect_hallucination
from services.classifier.failure_classifier import classify_failure
from services.explainer.explain import generate_explanation


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

    for claim in claims:

        verdict = verify_claim(claim)

        results.append(verdict)

    detection = detect_hallucination(results)
    hallucination = detection["hallucination"]
    reason = detection["reason"]

    if results and not hallucination and all(r.get("status") == "TRUE" for r in results):
        reason = "All extracted factual claims verified as true"

    error_type = classify_failure(results)
    explanation = generate_explanation(error_type)

    final_summary = {
        "hallucination": hallucination,
        "reason": reason,
        "notes": notes,
        "error_type": error_type,
        "explanation": explanation,
        "metrics": detection["metrics"],
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

    for verdict in results:

        print("\nClaim:", verdict["claim"])
        print("Verification:", verdict)

    print("\n--- ERROR TYPE ---")
    print(pipeline_output["summary"]["error_type"])

    print("\n--- EXPLANATION ---")
    print(pipeline_output["summary"]["explanation"])

    print("\nFinal Output:")
    print(pipeline_output["summary"])