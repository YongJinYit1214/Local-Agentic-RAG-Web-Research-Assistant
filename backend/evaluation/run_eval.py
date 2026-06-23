import json
from pathlib import Path

from app.routing import analyze_route


def main() -> None:
    cases_path = Path(__file__).with_name("eval_cases.json")
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    correct = 0
    rows: list[dict] = []

    for case in cases:
        decision = analyze_route(
            case["query"],
            case.get("web_search_mode", False),
            case.get("retrieval_confidence", 0.0),
        )
        predicted = decision.route.value
        expected = case["expected_route"]
        is_correct = predicted == expected
        correct += int(is_correct)
        rows.append(
            {
                "id": case["id"],
                "expected": expected,
                "predicted": predicted,
                "correct": is_correct,
                "confidence": decision.confidence,
            }
        )

    print(json.dumps({"route_accuracy": correct / len(cases), "cases": rows}, indent=2))


if __name__ == "__main__":
    main()
