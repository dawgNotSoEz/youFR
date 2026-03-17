import wikipedia


def get_evidence(claim: str) -> str:
    try:
        summary = wikipedia.summary(claim, sentences=3)
        return summary
    except Exception:
        return "No evidence found"
