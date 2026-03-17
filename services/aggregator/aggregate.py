def aggregate_results(results: list[dict]) -> dict:
    total = len(results)
    false_count = 0
    uncertain_count = 0
    low_confidence_count = 0

    for item in results:
        status = str(item.get("status", "UNCERTAIN")).upper()
        confidence = float(item.get("confidence", 0.0))

        if status == "FALSE":
            false_count += 1
        elif status == "UNCERTAIN":
            uncertain_count += 1
        elif confidence < 0.7:
            low_confidence_count += 1

    uncertain_ratio = (uncertain_count / total) if total else 0.0
    low_confidence_ratio = (low_confidence_count / total) if total else 0.0

    if false_count > 0:
        return {
            "hallucination": True,
            "reason": "False claims detected",
            "false_count": false_count,
            "uncertain_count": uncertain_count,
            "uncertain_ratio": uncertain_ratio,
            "low_confidence_count": low_confidence_count,
            "low_confidence_ratio": low_confidence_ratio,
            "total": total,
        }

    if uncertain_ratio > 0.5:
        return {
            "hallucination": True,
            "reason": "Too many unverifiable claims",
            "false_count": false_count,
            "uncertain_count": uncertain_count,
            "uncertain_ratio": uncertain_ratio,
            "low_confidence_count": low_confidence_count,
            "low_confidence_ratio": low_confidence_ratio,
            "total": total,
        }

    if low_confidence_ratio > 0.5:
        return {
            "hallucination": True,
            "reason": "Too many low-confidence claims",
            "false_count": false_count,
            "uncertain_count": uncertain_count,
            "uncertain_ratio": uncertain_ratio,
            "low_confidence_count": low_confidence_count,
            "low_confidence_ratio": low_confidence_ratio,
            "total": total,
        }

    return {
        "hallucination": False,
        "reason": "No hallucination",
        "false_count": false_count,
        "uncertain_count": uncertain_count,
        "uncertain_ratio": uncertain_ratio,
        "low_confidence_count": low_confidence_count,
        "low_confidence_ratio": low_confidence_ratio,
        "total": total,
    }
