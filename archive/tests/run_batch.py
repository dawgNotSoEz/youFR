import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.main_pipeline import run_pipeline


def run_batch() -> None:
    cases_path = ROOT_DIR / "tests" / "test_cases.json"
    test_cases = json.loads(cases_path.read_text(encoding="utf-8"))

    total = len(test_cases)
    matched = 0
    outputs = []

    for case in test_cases:
        query = case["query"]
        expected = case.get("expected_hallucination")

        result = run_pipeline(query)
        summary = result["summary"]
        predicted = summary.get("hallucination")

        is_match = expected is None or predicted == expected
        if is_match:
            matched += 1

        outputs.append(
            {
                "query": query,
                "expected_hallucination": expected,
                "predicted_hallucination": predicted,
                "match": is_match,
                "reason": summary.get("reason"),
                "error_type": summary.get("error_type"),
            }
        )

    accuracy = (matched / total) if total else 0.0
    report = {
        "total_cases": total,
        "matched_cases": matched,
        "accuracy": accuracy,
        "outputs": outputs,
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_batch()
