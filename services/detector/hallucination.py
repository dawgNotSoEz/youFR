from services.aggregator.aggregate import aggregate_results


def detect_hallucination(results: list[dict]) -> dict:
    aggregated = aggregate_results(results)
    return {
        "hallucination": aggregated["hallucination"],
        "reason": aggregated["reason"],
        "metrics": {
            "total": aggregated["total"],
            "false_count": aggregated["false_count"],
            "uncertain_count": aggregated["uncertain_count"],
            "uncertain_ratio": aggregated["uncertain_ratio"],
            "low_confidence_count": aggregated["low_confidence_count"],
            "low_confidence_ratio": aggregated["low_confidence_ratio"],
        },
    }
