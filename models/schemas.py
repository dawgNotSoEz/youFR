class ClaimResult:
    def __init__(self, claim, status, confidence, reason):
        self.claim = claim
        self.status = status
        self.confidence = confidence
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "claim": self.claim,
            "status": self.status,
            "confidence": self.confidence,
            "reason": self.reason,
        }
