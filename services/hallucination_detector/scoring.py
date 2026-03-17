def detect_hallucination(results):
    false_claims = [r for r in results if r.get("status") == "FALSE"]
    uncertain_claims = [r for r in results if r.get("status") == "UNCERTAIN"]

    if false_claims:
        return True, "False claims detected"

    if results and len(uncertain_claims) > len(results) * 0.5:
        return True, "Too many unverifiable claims"

    return False, "No hallucination"