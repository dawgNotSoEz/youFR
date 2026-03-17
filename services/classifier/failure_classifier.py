def _extract_status(verdict):
    if isinstance(verdict, dict):
        return str(verdict.get("status", "UNCERTAIN")).upper()

    if isinstance(verdict, str):
        lower = verdict.lower()
        if "false" in lower:
            return "FALSE"
        if "uncertain" in lower:
            return "UNCERTAIN"
        if "true" in lower:
            return "TRUE"

    if isinstance(verdict, tuple) and len(verdict) >= 2:
        return _extract_status(verdict[1])

    return "UNCERTAIN"


def classify_failure(results):
    false_count = sum(1 for item in results if _extract_status(item) == "FALSE")
    uncertain_count = sum(1 for item in results if _extract_status(item) == "UNCERTAIN")

    if false_count > 0:
        return "FACTUAL_ERROR"

    if uncertain_count > len(results) / 2:
        return "UNVERIFIABLE"

    if len(results) == 0:
        return "CLAIM_EXTRACTION_ERROR"

    return "VALID"
