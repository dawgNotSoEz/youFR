def fuse_results(llm_result, evidence_result):
    llm_status = str((llm_result or {}).get("status", "UNCERTAIN")).upper()
    evidence_status = str((evidence_result or {}).get("status", "UNCERTAIN")).upper()

    try:
        llm_confidence = float((llm_result or {}).get("confidence", 0.0))
    except Exception:
        llm_confidence = 0.0

    try:
        evidence_confidence = float((evidence_result or {}).get("confidence", 0.0))
    except Exception:
        evidence_confidence = 0.0

    if llm_status == "FALSE" or evidence_status == "FALSE":
        return {
            "final_status": "FALSE",
            "reason": "At least one verifier marked FALSE",
        }

    if llm_status != evidence_status:
        return {
            "final_status": "UNCERTAIN",
            "reason": "Disagreement between verifiers",
        }

    if min(llm_confidence, evidence_confidence) < 0.7:
        return {
            "final_status": "UNCERTAIN",
            "reason": "Low confidence",
        }

    return {
        "final_status": "TRUE",
        "reason": "Both verifiers agree with high confidence",
    }


def aggregate_results(results: list[dict]) -> dict:
    total_claims = len(results)
    false_count = 0
    uncertain_count = 0
    fused_results = []

    for item in results:
        claim = item.get("claim", "")
        llm_result = item.get("llm", {})
        evidence_result = item.get("evidence", {})

        fused = fuse_results(llm_result, evidence_result)
        fused_results.append(
            {
                "claim": claim,
                "llm": llm_result,
                "evidence": evidence_result,
                "fused": fused,
            }
        )

        final_status = fused.get("final_status", "UNCERTAIN")
        if final_status == "FALSE":
            false_count += 1
        elif final_status == "UNCERTAIN":
            uncertain_count += 1

    uncertain_ratio = (uncertain_count / total_claims) if total_claims else 0.0
    hallucination = bool(false_count > 0 or uncertain_ratio > 0.5)

    if false_count > 0:
        reason = "False claims detected after fusion"
    elif uncertain_ratio > 0.5:
        reason = "Too many uncertain claims after fusion"
    else:
        reason = "No hallucination after fusion"

    return {
        "hallucination": hallucination,
        "reason": reason,
        "total_claims": total_claims,
        "false_count": false_count,
        "uncertain_count": uncertain_count,
        "uncertain_ratio": uncertain_ratio,
        "fused_results": fused_results,
    }
