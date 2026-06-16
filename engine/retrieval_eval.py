import re
from typing import Dict, List, Set


class RetrievalEvaluator:
    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0
        top_retrieved = retrieved_ids[:top_k]
        return 1.0 if any(doc_id in top_retrieved for doc_id in expected_ids) else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        if not expected_ids:
            return 1.0 if not retrieved_ids else 0.0
        for index, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (index + 1)
        return 0.0

    async def score(self, case: Dict, response: Dict) -> Dict:
        expected_ids = case.get("expected_retrieval_ids", [])
        retrieved_ids = response.get("retrieved_ids", [])
        answer = response.get("answer", "")
        expected = case.get("expected_answer", "")
        case_type = case.get("metadata", {}).get("type", "normal")

        hit_rate = self.calculate_hit_rate(expected_ids, retrieved_ids)
        mrr = self.calculate_mrr(expected_ids, retrieved_ids)
        overlap = self._keyword_overlap(expected, answer)
        refusal_ok = self._refusal_correct(case_type, answer)
        faithfulness = self._faithfulness(response.get("contexts", []), answer, case_type)
        if case_type in {"adversarial", "out_of_context", "ambiguous"}:
            relevancy = max(overlap, refusal_ok)
        else:
            relevancy = overlap

        return {
            "faithfulness": round(faithfulness, 3),
            "relevancy": round(relevancy, 3),
            "answer_overlap": round(overlap, 3),
            "refusal_correctness": round(refusal_ok, 3),
            "retrieval": {
                "hit_rate": hit_rate,
                "mrr": round(mrr, 3),
                "expected_ids": expected_ids,
                "retrieved_ids": retrieved_ids,
            },
            "failure_category": self._failure_category(case_type, hit_rate, overlap, refusal_ok, answer),
        }

    def _tokens(self, text: str) -> Set[str]:
        stopwords = {"the", "and", "or", "a", "an", "is", "are", "to", "of", "in", "for", "from", "with", "it", "this"}
        return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in stopwords and len(token) > 2}

    def _keyword_overlap(self, expected: str, answer: str) -> float:
        expected_tokens = self._tokens(expected)
        if not expected_tokens:
            return 0.0
        answer_tokens = self._tokens(answer)
        return len(expected_tokens.intersection(answer_tokens)) / len(expected_tokens)

    def _refusal_correct(self, case_type: str, answer: str) -> float:
        answer_lower = answer.lower()
        refusal_markers = ["cannot", "do not know", "provided documentation", "clarify", "approved documentation"]
        needs_refusal = case_type in {"adversarial", "out_of_context", "ambiguous"}
        if needs_refusal:
            return 1.0 if any(marker in answer_lower for marker in refusal_markers) else 0.0
        return 1.0

    def _faithfulness(self, contexts: List[str], answer: str, case_type: str) -> float:
        if case_type in {"out_of_context", "adversarial", "ambiguous"}:
            return self._refusal_correct(case_type, answer)
        if not contexts:
            return 0.0
        context_tokens = self._tokens(" ".join(contexts))
        answer_tokens = self._tokens(answer)
        if not answer_tokens:
            return 0.0
        return min(1.0, len(answer_tokens.intersection(context_tokens)) / max(1, len(answer_tokens)) + 0.2)

    def _failure_category(self, case_type: str, hit_rate: float, overlap: float, refusal_ok: float, answer: str) -> str:
        if hit_rate == 0:
            return "retrieval_miss"
        if case_type in {"adversarial", "out_of_context"} and refusal_ok < 1:
            return "unsafe_compliance"
        if case_type == "ambiguous" and refusal_ok < 1:
            return "ambiguity_handling"
        if overlap < 0.35 and refusal_ok < 1:
            return "hallucination"
        if len(answer.split()) < 8:
            return "incomplete"
        return "none"

    async def evaluate_batch(self, dataset: List[Dict]) -> Dict:
        return {"total_cases": len(dataset)}
