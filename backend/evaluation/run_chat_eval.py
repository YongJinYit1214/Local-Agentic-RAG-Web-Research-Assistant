"""Run the seeded PDF test set through the actual streaming API."""

import argparse
import asyncio
import csv
import json
import re
import uuid
from collections import Counter
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[2]
REFUSAL = re.compile(r"can(?:not|'t) answer|not (?:mentioned|specified|provided|covered)|no (?:evidence|information)|does not (?:mention|contain)|cannot be determined", re.I)
NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")
NUMBER_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "seven": "7", "twelve": "12", "thirty": "30", "fifty": "50", "ninety": "90"}


async def ask(client: httpx.AsyncClient, base_url: str, question: str, session_id: str) -> dict:
    result = {"answer": "", "route": None, "sources": [], "verification": None, "done": False, "errors": [], "events": []}
    try:
        async with client.stream("POST", f"{base_url}/chat/stream", json={
            "session_id": session_id, "message": question, "web_search_mode": False,
        }) as response:
            response.raise_for_status()
            event = None
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    event = line[7:]
                elif line.startswith("data: ") and event:
                    payload = json.loads(line[6:])
                    result["events"].append(event)
                    if event == "token":
                        result["answer"] += payload.get("token", "")
                    elif event == "route":
                        result["route"] = payload
                    elif event == "sources":
                        result["sources"] = payload.get("sources", [])
                    elif event == "verification":
                        result["verification"] = payload.get("verification")
                    elif event == "done":
                        result["done"] = True
                    elif event == "error":
                        result["errors"].append(payload.get("message", str(payload)))
                    event = None
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    return result


def assess(case: dict, result: dict) -> dict:
    expected = case["expected_answer"]
    actual = result["answer"]
    expected_refusal = case["type"] == "out_of_scope_trap" or expected.startswith("NOT ANSWERABLE")
    refused = bool(REFUSAL.search(actual)) and not bool(re.search(r"\b(?:no|not)\b.{0,100}\b(?:test|tested|allow|allowed|permit|permitted)\b", actual, re.I))
    if case["id"] == "Q26":
        refused = bool(re.search(r"(?:cannot|not|no)\s+(?:be\s+)?meaningfully\s+compar|unrelated\s+(?:attributes|facts|metrics)", actual, re.I))
    source_documents = [source.get("document") or source.get("title", "") for source in result["sources"]]
    sources_available = "sources" in result["events"]
    source_hit = None if not sources_available else case["source_document"] == "N/A" or any(case["source_document"] in name for name in source_documents)
    numbers = NUMBER.findall(expected) if not expected_refusal else []
    actual_numbers = set(NUMBER.findall(actual)) | {value for word, value in NUMBER_WORDS.items() if re.search(rf"\b{word}\b", actual.lower())}
    missing_numbers = [value for value in numbers if value not in actual_numbers]
    issues = []
    if result["errors"]:
        issues.append("stream_error")
    if not result["done"]:
        issues.append("incomplete_stream")
    if expected_refusal and not refused:
        issues.append("missing_refusal")
    if not expected_refusal and refused:
        issues.append("false_refusal")
    if not expected_refusal and source_hit is False:
        issues.append("expected_source_missing")
    if not sources_available and not expected_refusal:
        issues.append("sources_event_missing")
    if missing_numbers:
        issues.append("expected_numbers_missing")
    if result["route"] and not expected_refusal and result["route"]["route"] != "RAG":
        issues.append("unexpected_route")
    return {
        **case, **result, "source_documents": source_documents, "sources_available": sources_available,
        "expected_refusal": expected_refusal, "refused": refused,
        "source_hit": source_hit, "missing_numbers": missing_numbers,
        "issues": issues, "needs_semantic_review": not expected_refusal and not issues,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8011")
    parser.add_argument("--csv", type=Path, default=ROOT / "rag_test_set.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "backend/evaluation/results")
    parser.add_argument("--reassess", action="store_true", help="Regrade saved API responses without calling the model")
    args = parser.parse_args()
    cases = list(csv.DictReader(args.csv.open(encoding="utf-8-sig", newline="")))
    results = []
    saved = {}
    if args.reassess:
        saved = {row["id"]: row for row in json.loads((args.output / "chat_eval.json").read_text(encoding="utf-8"))}
    async with httpx.AsyncClient(timeout=httpx.Timeout(240, connect=15)) as client:
        for case in cases:
            result = saved[case["id"]] if args.reassess else await ask(client, args.base_url, case["question"], f"eval-{case['id']}-{uuid.uuid4().hex}")
            row = assess(case, result)
            results.append(row)
            print(f"{case['id']}: {row['route']['route'] if row['route'] else 'NONE'}; {','.join(row['issues']) or 'automated checks clear'}", flush=True)

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "chat_eval.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = Counter(issue for row in results for issue in row["issues"])
    lines = ["# End-to-end chat evaluation", "", f"Cases: {len(results)}", "", "## Automated issue counts", ""]
    lines.extend(f"- {issue}: {count}" for issue, count in sorted(counts.items()))
    lines += ["", "Automated checks do not prove semantic correctness. Inspect each answer below against the expected answer and PDF.", "", "## Cases", ""]
    for row in results:
        route = row["route"]["route"] if row["route"] else "NONE"
        lines += [f"### {row['id']} ({row['type']})", "", f"Question: {row['question']}", "", f"Expected: {row['expected_answer']}", "", f"Route: {route}; source hit: {row['source_hit']}; done: {row['done']}; issues: {', '.join(row['issues']) or 'none detected'}", "", f"Sources: {', '.join(row['source_documents']) or 'none'}", "", f"Actual: {row['answer'] or '[empty]'}", ""]
        if row["errors"]:
            lines += [f"Errors: {'; '.join(row['errors'])}", ""]
    (args.output / "chat_eval.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Reports: {args.output / 'chat_eval.md'} and {args.output / 'chat_eval.json'}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
