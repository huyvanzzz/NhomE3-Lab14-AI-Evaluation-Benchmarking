import asyncio
import time
from typing import Dict, List


class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()
        response = await self.agent.query(test_case["question"])
        latency = time.perf_counter() - start_time

        eval_scores = await self.evaluator.score(test_case, response)
        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"],
            response["answer"],
            test_case["expected_answer"],
            test_case,
        )

        failure_category = eval_scores["failure_category"]
        if failure_category == "none" and judge_result["final_score"] < 3:
            failure_category = "low_judge_score"
        status = "pass" if judge_result["final_score"] >= 3 and failure_category == "none" else "fail"
        metadata = response.get("metadata", {})
        return {
            "case_id": test_case.get("id"),
            "test_case": test_case["question"],
            "case_type": test_case.get("metadata", {}).get("type", "normal"),
            "expected_answer": test_case.get("expected_answer"),
            "agent_response": response["answer"],
            "contexts": response.get("contexts", []),
            "retrieved_ids": response.get("retrieved_ids", []),
            "latency": round(latency, 4),
            "tokens_used": metadata.get("tokens_used", 0),
            "cost_usd": metadata.get("cost_usd", 0.0),
            "ragas": eval_scores,
            "judge": judge_result,
            "failure_category": failure_category,
            "status": status,
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 10) -> List[Dict]:
        results = []
        for index in range(0, len(dataset), batch_size):
            batch = dataset[index:index + batch_size]
            batch_results = await asyncio.gather(*(self.run_single_test(case) for case in batch))
            results.extend(batch_results)
        return results
