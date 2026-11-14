import inspect
import unittest

from app.prompts import build_messages
from app.routing import analyze_route
from app.schemas import Source
from app.services.structured_llm import verify_grounded_answer


class ChatRegressions(unittest.TestCase):
    def test_verifier_call_contract(self):
        parameters = inspect.signature(verify_grounded_answer).parameters
        self.assertEqual({"question", "answer", "context", "sources"} - parameters.keys(), set())

    def test_relevant_match_below_old_threshold_routes_to_rag(self):
        decision = analyze_route("How often must employees change passwords?", False, 0.72, 0.57, 5)
        self.assertEqual(decision.route, "RAG")

    def test_weak_match_still_refuses(self):
        decision = analyze_route("What is the annual leave entitlement?", False, 0.67, 0.42, 1)
        self.assertEqual(decision.route, "CHAT")

    def test_policy_context_is_not_cut_at_1200_characters(self):
        evidence = "A" * 1500 + " Restricted data may not be printed."
        prompt = build_messages("Can Restricted data be printed?", [], "RAG", [evidence], [Source(title="policy page 1")])[-1]["content"]
        self.assertIn("Restricted data may not be printed.", prompt)


if __name__ == "__main__":
    unittest.main()
