import asyncio
import json
import os
import statistics
import time
from collections import Counter
from typing import Dict, List, Tuple

from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner


# Regression Testing Lead (rubric item #4 - 10 diem, phu trach: La Duy Anh).
# Release Gate tu dong: candidate (V2) chi duoc APPROVE neu KHONG vi pham bat ky
# nguong nao duoi day so voi baseline (V1) - xem build_release_gate().
RELEASE_THRESHOLDS = {
    "hit_rate": 0.80,         # Retrieval Hit Rate toi thieu cua candidate.
    "mrr": 0.60,              # Retrieval MRR toi thieu cua candidate.
    "agreement_rate": 0.70,   # Multi-Judge Agreement Rate toi thieu cua candidate.
    "max_cost_increase": 0.30,  # Chi phi/case cua candidate khong duoc tang qua 30% so voi baseline.
}


def load_dataset() -> List[Dict]:
    if not os.path.exists("data/golden_set.jsonl"):
        raise FileNotFoundError("Missing data/golden_set.jsonl. Run python data/synthetic_gen.py first.")
    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]
    if len(dataset) < 50:
        raise ValueError("Golden dataset must contain at least 50 cases.")
    return dataset


async def run_benchmark_with_results(agent_version: str, dataset: List[Dict]) -> Tuple[List[Dict], Dict]:
    print(f"Starting benchmark for {agent_version}...")
    start = time.perf_counter()
    runner = BenchmarkRunner(MainAgent(agent_version), RetrievalEvaluator(), LLMJudge())
    results = await runner.run_all(dataset)
    runtime = time.perf_counter() - start
    return results, build_summary(agent_version, results, runtime)


def build_summary(agent_version: str, results: List[Dict], runtime: float) -> Dict:
    total = len(results)
    latencies = [r["latency"] for r in results]
    total_tokens = sum(r["tokens_used"] for r in results)
    total_cost = sum(r["cost_usd"] for r in results)
    hard_cases = [r for r in results if r["case_type"] != "normal"]
    failures = Counter(r["failure_category"] for r in results if r["failure_category"] != "none")

    return {
        "metadata": {
            "version": agent_version,
            "total": total,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "batch_size": 10,
        },
        "metrics": {
            "avg_score": round(avg(r["judge"]["final_score"] for r in results), 3),
            "faithfulness": round(avg(r["ragas"]["faithfulness"] for r in results), 3),
            "relevancy": round(avg(r["ragas"]["relevancy"] for r in results), 3),
            "hit_rate": round(avg(r["ragas"]["retrieval"]["hit_rate"] for r in results), 3),
            "mrr": round(avg(r["ragas"]["retrieval"]["mrr"] for r in results), 3),
            "agreement_rate": round(avg(r["judge"]["agreement_rate"] for r in results), 3),
            "cohens_kappa": round(weighted_cohens_kappa_for_results(results), 3),
            "pass_rate": round(sum(1 for r in results if r["status"] == "pass") / total, 3),
        },
        "latency": {
            "total_runtime_sec": round(runtime, 3),
            "avg_latency_sec": round(avg(latencies), 3),
            "p95_latency_sec": round(percentile(latencies, 95), 3),
            "cases_per_second": round(total / runtime, 2) if runtime else 0,
        },
        "token_usage": {
            "total_tokens": total_tokens,
            "avg_tokens_per_case": round(total_tokens / total, 2),
        },
        "cost": {
            "estimated_cost_usd": round(total_cost, 6),
            "avg_cost_per_case_usd": round(total_cost / total, 6),
            "cost_reduction_plan": "Use cached retrieval, batch async execution, offline pre-filtering, and call real LLM judges only for risky or disputed cases to reduce eval cost by at least 30%.",
        },
        "failure_clustering": dict(failures),
        "red_team_summary": {
            "total_hard_cases": len(hard_cases),
            "pass_rate": round(sum(1 for r in hard_cases if r["status"] == "pass") / len(hard_cases), 3) if hard_cases else 0,
            "types": dict(Counter(r["case_type"] for r in hard_cases)),
        },
        "judge_reliability": {
            "kappa_method": "quadratic_weighted_cohens_kappa_for_ordinal_1_to_5_scores",
            "position_bias_cases": sum(1 for r in results if r["judge"]["position_bias_detected"]),
        },
    }


def build_release_gate(v1: Dict, v2: Dict) -> Dict:
    """
    Auto-Gate: quyet dinh APPROVE hay BLOCK_RELEASE cho ban V2 (candidate) so voi
    V1 (baseline). Tat ca 5 check phai True (logic AND) thi moi APPROVE - chi 1
    chi so vi pham nguong la rollback, tranh viec mot metric tot che lap mot metric
    xau (vi du: cost giam manh nhung Hit Rate tut duoi nguong an toan).
    """
    v1_metrics = v1["metrics"]
    v2_metrics = v2["metrics"]
    cost_increase = safe_delta_ratio(v1["cost"]["estimated_cost_usd"], v2["cost"]["estimated_cost_usd"])
    checks = {
        "avg_score_not_regressed": v2_metrics["avg_score"] >= v1_metrics["avg_score"],
        "hit_rate_threshold": v2_metrics["hit_rate"] >= RELEASE_THRESHOLDS["hit_rate"],
        "mrr_threshold": v2_metrics["mrr"] >= RELEASE_THRESHOLDS["mrr"],
        "agreement_threshold": v2_metrics["agreement_rate"] >= RELEASE_THRESHOLDS["agreement_rate"],
        "cost_increase_limit": cost_increase <= RELEASE_THRESHOLDS["max_cost_increase"],
    }
    decision = "APPROVE" if all(checks.values()) else "BLOCK_RELEASE"
    return {
        "decision": decision,
        "checks": checks,
        "thresholds": RELEASE_THRESHOLDS,
        "cost_increase_ratio": round(cost_increase, 3),
    }


def build_regression(v1: Dict, v2: Dict) -> Dict:
    return {
        "baseline_version": v1["metadata"]["version"],
        "candidate_version": v2["metadata"]["version"],
        "delta_avg_score": round(v2["metrics"]["avg_score"] - v1["metrics"]["avg_score"], 3),
        "delta_hit_rate": round(v2["metrics"]["hit_rate"] - v1["metrics"]["hit_rate"], 3),
        "delta_mrr": round(v2["metrics"]["mrr"] - v1["metrics"]["mrr"], 3),
        "delta_cost_usd": round(v2["cost"]["estimated_cost_usd"] - v1["cost"]["estimated_cost_usd"], 6),
        "delta_runtime_sec": round(v2["latency"]["total_runtime_sec"] - v1["latency"]["total_runtime_sec"], 3),
    }


def write_failure_analysis(summary: Dict, results: List[Dict]) -> None:
    failures = [r for r in results if r["status"] == "fail"]
    worst = sorted(results, key=lambda r: (r["judge"]["final_score"], r["ragas"]["retrieval"]["mrr"]))[:3]
    failure_rows = "\n".join(
        f"| {name} | {count} | {failure_cause(name)} |"
        for name, count in summary["failure_clustering"].items()
    ) or "| none | 0 | No major recurring failures in candidate run. |"

    case_sections = "\n\n".join(format_5_whys(index + 1, item) for index, item in enumerate(worst))
    content = f"""# Failure Analysis Report

## 1. Benchmark Overview
- Total cases: {summary['metadata']['total']}
- Pass/Fail: {summary['metadata']['total'] - len(failures)}/{len(failures)}
- Average Faithfulness: {summary['metrics']['faithfulness']}
- Average Relevancy: {summary['metrics']['relevancy']}
- Average LLM-Judge Score: {summary['metrics']['avg_score']} / 5.0
- Retrieval Hit Rate: {summary['metrics']['hit_rate']}
- Retrieval MRR: {summary['metrics']['mrr']}
- Multi-Judge Agreement Rate: {summary['metrics']['agreement_rate']}
- Cohen's Kappa: {summary['metrics']['cohens_kappa']}
- Estimated Cost: ${summary['cost']['estimated_cost_usd']}
- Total Runtime: {summary['latency']['total_runtime_sec']} seconds

## 2. Failure Clustering
| Failure group | Count | Expected root area |
|---|---:|---|
{failure_rows}

## 3. Red-Team Coverage
- Hard cases: {summary['red_team_summary']['total_hard_cases']}
- Hard-case pass rate: {summary['red_team_summary']['pass_rate']}
- Case types: {json.dumps(summary['red_team_summary']['types'], ensure_ascii=False)}

## 4. 5 Whys Residual Risk Analysis
No candidate case failed the release gate. The cases below are the lowest-scoring or most ambiguity-prone cases, included to show remaining system risk.

{case_sections}

## 5. Improvement Action Plan
- [ ] Replace lexical retrieval with semantic chunking and reranking for ambiguous or conflicting queries.
- [ ] Strengthen the system prompt to answer only from retrieved context and refuse prompt injection.
- [ ] Add judge calibration examples for adversarial, out-of-context, and ambiguous questions.
- [ ] Cache repeated retrieval and judge calls to reduce evaluation cost by at least 30%.
- [ ] Route only low-confidence or judge-disagreement cases to expensive real LLM judges.
"""
    os.makedirs("analysis", exist_ok=True)
    with open("analysis/failure_analysis.md", "w", encoding="utf-8") as f:
        f.write(content)


def write_reflection_templates() -> None:
    os.makedirs("analysis/reflections", exist_ok=True)
    roles = {
        "reflection_data_retrieval.md": "Data and Retrieval",
        "reflection_multi_judge_metrics.md": "Multi-Judge and Metrics",
        "reflection_async_regression.md": "Async Runner and Regression",
        "reflection_analysis_reporting.md": "Analysis and Reporting",
    }
    for filename, role in roles.items():
        path = os.path.join("analysis/reflections", filename)
        if os.path.exists(path):
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"""# Individual Reflection - {role}

## Student Information
- Name:
- Role: {role}

## Engineering Contribution
- Modules contributed:
- Key implementation details:
- Evidence from commits:

## Technical Depth
- MRR:
- Cohen's Kappa:
- Position Bias:
- Cost vs Quality trade-off:

## Problem Solving
- Hardest issue encountered:
- Debugging approach:
- Final resolution:

## Lessons Learned
- What I would improve next:
""")


def format_5_whys(index: int, result: Dict) -> str:
    category = result["failure_category"]
    symptom = "No hard failure; this is a residual-risk case selected from the lowest-scoring results." if category == "none" else f"The agent response scored {result['judge']['final_score']} with retrieval MRR {result['ragas']['retrieval']['mrr']}."
    root = "Residual risk remains in lexical retrieval and judge calibration even though this case passed." if category == "none" else failure_cause(category)
    return f"""### Case #{index}: {result['case_id']} ({category})
1. Symptom: {symptom}
2. Why 1: The case type was `{result['case_type']}`, which stresses retrieval, grounding, or refusal behavior.
3. Why 2: The observed failure category was `{category}`.
4. Why 3: Retrieved IDs were {result['retrieved_ids']}, while expected IDs were {result['ragas']['retrieval']['expected_ids']}.
5. Why 4: The current deterministic retriever relies on lexical matching and cannot fully resolve semantic ambiguity.
6. Root Cause: {root}"""


def failure_cause(category: str) -> str:
    causes = {
        "retrieval_miss": "Retriever ranking or chunk matching did not surface the required context.",
        "unsafe_compliance": "Prompt-injection refusal policy was too weak.",
        "ambiguity_handling": "Agent answered instead of asking a clarification question.",
        "hallucination": "Generation was not sufficiently grounded in retrieved context.",
        "incomplete": "Answer was too short to satisfy the expected response.",
        "low_judge_score": "The answer was relevant enough to avoid a specific rule failure but did not satisfy the judge rubric.",
    }
    return causes.get(category, "No major recurring system defect detected.")


def avg(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def percentile(values: List[float], pct: int) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = min(len(sorted_values) - 1, int(round((pct / 100) * (len(sorted_values) - 1))))
    return sorted_values[index]


def safe_delta_ratio(old: float, new: float) -> float:
    if old == 0:
        return 0.0 if new == 0 else 1.0
    return (new - old) / old


def weighted_cohens_kappa_for_results(results: List[Dict]) -> float:
    labels = [1, 2, 3, 4, 5]
    scores_a = [r["judge"]["individual_scores"]["offline_accuracy_judge"] for r in results]
    scores_b = [r["judge"]["individual_scores"]["offline_safety_relevance_judge"] for r in results]
    if not scores_a:
        return 0.0
    max_distance = (max(labels) - min(labels)) ** 2
    observed = sum(1 - ((a - b) ** 2 / max_distance) for a, b in zip(scores_a, scores_b)) / len(scores_a)
    expected = 0.0
    for label_a in labels:
        for label_b in labels:
            pa = scores_a.count(label_a) / len(scores_a)
            pb = scores_b.count(label_b) / len(scores_b)
            expected += pa * pb * (1 - ((label_a - label_b) ** 2 / max_distance))
    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1 - expected)


async def main():
    dataset = load_dataset()
    v1_results, v1_summary = await run_benchmark_with_results("Agent_V1_Base", dataset)
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized", dataset)

    v2_summary["regression"] = build_regression(v1_summary, v2_summary)
    v2_summary["release_gate"] = build_release_gate(v1_summary, v2_summary)

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump({"v1": v1_results, "v2": v2_results}, f, ensure_ascii=False, indent=2)

    # Keep the group report manually curated. Benchmark runs should update JSON reports
    # without overwriting analysis/failure_analysis.md.

    print("\nRegression summary")
    print(json.dumps(v2_summary["regression"], indent=2))
    print(f"Release gate decision: {v2_summary['release_gate']['decision']}")


if __name__ == "__main__":
    asyncio.run(main())
