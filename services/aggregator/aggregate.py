def fuse(llm, evidence, embedding):
    llm_status = str((llm or {}).get("status", "UNCERTAIN")).upper()
    evidence_status = str((evidence or {}).get("status", "UNCERTAIN")).upper()

    try:
        llm_confidence = float((llm or {}).get("confidence", 0.0))
    except Exception:
        llm_confidence = 0.0

    try:
        evidence_confidence = float((evidence or {}).get("confidence", 0.0))
    except Exception:
        evidence_confidence = 0.0

    try:
        embedding_score = float((embedding or {}).get("score", 0.0))
    except Exception:
        embedding_score = 0.0

    if llm_status == "FALSE" or evidence_status == "FALSE":
        return {
            "final_status": "FALSE",
            "reason": "One verifier FALSE",
        }

    if llm_status != evidence_status:
        return {
            "final_status": "UNCERTAIN",
            "reason": "Verifier disagreement",
        }

    if embedding_score < 0.5:
        return {
            "final_status": "UNCERTAIN",
            "reason": "Low semantic similarity",
        }

    if llm_confidence < 0.7 or evidence_confidence < 0.7:
        return {
            "final_status": "UNCERTAIN",
            "reason": "Low confidence",
        }

    return {
        "final_status": "TRUE",
        "reason": "All signals agree",
    }


def fuse_results(llm_result, evidence_result, embedding_result=None):
    return fuse(llm_result, evidence_result, embedding_result or {"score": 1.0})


def aggregate_results(results: list[dict]) -> dict:
    total_claims = len(results)
    false_count = 0
    uncertain_count = 0
    fused_results = []

    for item in results:
        claim = item.get("claim", "")
        llm_result = item.get("llm", {})
        evidence_result = item.get("evidence", {})
        embedding_result = item.get("embedding", {"score": 1.0})

        fused = fuse(llm_result, evidence_result, embedding_result)
        fused_results.append(
            {
                "claim": claim,
                "llm": llm_result,
                "evidence": evidence_result,
                "embedding": embedding_result,
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
