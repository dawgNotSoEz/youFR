import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.llm_generator.generate import generate_answer, get_last_call_info
from services.claim_extractor.extractor import extract_claims
from services.verifier.groq_verifier import verify_claim


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

    claims = extract_claims(answer)

    print("\nExtracted Claims:\n", claims)

    results = []

    for claim in claims:

        verdict = verify_claim(claim)

        results.append((claim, verdict))

    return results


if __name__ == "__main__":

    query = "Who invented relativity?"

    results = run_pipeline(query)

    for claim, verdict in results:

        print("\nClaim:", claim)
        print("Verification:", verdict)