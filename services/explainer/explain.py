def generate_explanation(error_type):
    explanations = {
        "FACTUAL_ERROR": "The model produced incorrect factual information.",
        "UNVERIFIABLE": "The claims could not be verified with confidence.",
        "CLAIM_EXTRACTION_ERROR": "The system failed to extract meaningful claims.",
        "VALID": "The response appears factually correct.",
    }

    return explanations.get(error_type, "Unknown error")
