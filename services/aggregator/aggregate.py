def fuse(llm, evidence, embedding, local):
    llm_status = str((llm or {}).get("status", "UNCERTAIN")).upper()
    evidence_status = str((evidence or {}).get("status", "UNCERTAIN")).upper()
    local_status = str((local or {}).get("status", "UNCERTAIN")).upper()

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

    if llm_status == "FALSE" or evidence_status == "FALSE" or local_status == "FALSE":
        return {"final_status": "FALSE", "reason": "One verifier FALSE"}

    local_active = local_status != "UNCERTAIN"
    _ = local_active

    if (
        llm_status == "TRUE"
        and evidence_status == "TRUE"
        and llm_confidence >= 0.7
        and evidence_confidence >= 0.7
        and embedding_score >= 0.5
    ):
        return {"final_status": "TRUE", "reason": "Strong consensus (LLM + Evidence)"}

    if llm_status == evidence_status:
        return {"final_status": "UNCERTAIN", "reason": "Weak agreement"}

    return {"final_status": "UNCERTAIN", "reason": "Insufficient agreement"}


def fuse_results(llm_result, evidence_result, embedding_result=None):
    return fuse(
        llm_result,
        evidence_result,
        embedding_result or {"score": 1.0},
        {"status": "UNCERTAIN", "confidence": 0.0},
    )


def aggregate_results(results: list[dict]) -> dict:
    total_claims = len(results)
    false_count = 0
    uncertain_count = 0
    fused_results = []

    for item in results:
        claim = item.get("claim", "")
        llm_result = item.get("llm", {})
        evidence_result = item.get("evidence", {})
        local_result = item.get("local") or {"status": "UNCERTAIN", "confidence": 0.0}
        embedding_result = item.get("embedding", {"score": 1.0})

        fused = fuse(llm_result, evidence_result, embedding_result, local_result)
        fused_results.append(
            {
                "claim": claim,
                "llm": llm_result,
                "evidence": evidence_result,
                "local": local_result,
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
