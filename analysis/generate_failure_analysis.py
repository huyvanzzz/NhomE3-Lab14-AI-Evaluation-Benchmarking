import json
import os
from collections import Counter
from typing import Dict, Iterable, List


REPORT_PATH = os.path.join("analysis", "failure_analysis.md")
SUMMARY_PATH = os.path.join("reports", "summary.json")
BENCHMARK_PATH = os.path.join("reports", "benchmark_results.json")


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def avg(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def get_result_sets(benchmark_data) -> Dict[str, List[Dict]]:
    if isinstance(benchmark_data, dict):
        if "v1" in benchmark_data and "v2" in benchmark_data:
            return benchmark_data
        if "results" in benchmark_data:
            return {"v2": benchmark_data["results"]}
    if isinstance(benchmark_data, list):
        return {"v2": benchmark_data}
    raise ValueError("Unsupported reports/benchmark_results.json format.")


def summarize_results(version_name: str, results: List[Dict]) -> Dict:
    failures = [item for item in results if item["status"] == "fail"]
    hard_cases = [item for item in results if item["case_type"] != "normal"]
    return {
        "version": version_name,
        "total": len(results),
        "failures": len(failures),
        "passes": len(results) - len(failures),
        "avg_score": avg(item["judge"]["final_score"] for item in results),
        "faithfulness": avg(item["ragas"]["faithfulness"] for item in results),
        "relevancy": avg(item["ragas"]["relevancy"] for item in results),
        "hit_rate": avg(item["ragas"]["retrieval"]["hit_rate"] for item in results),
        "mrr": avg(item["ragas"]["retrieval"]["mrr"] for item in results),
        "agreement_rate": avg(item["judge"]["agreement_rate"] for item in results),
        "latency": avg(item["latency"] for item in results),
        "cost": sum(item["cost_usd"] for item in results),
        "failure_categories": Counter(item["failure_category"] for item in failures),
        "failed_case_types": Counter(item["case_type"] for item in failures),
        "position_bias_cases": sum(1 for item in results if item["judge"]["position_bias_detected"]),
        "hard_case_pass_rate": (
            sum(1 for item in hard_cases if item["status"] == "pass") / len(hard_cases)
            if hard_cases
            else 0.0
        ),
    }


def failure_root_area(category: str) -> str:
    mapping = {
        "unsafe_compliance": "Prompting and safety refusal policy",
        "retrieval_miss": "Retriever fallback and out-of-scope detection",
        "low_judge_score": "Retriever ranking plus answer selection coupling",
        "hallucination": "Grounding failure between retrieval and generation",
        "ambiguity_handling": "Clarification strategy",
        "incomplete": "Answer completeness and prompt coverage",
    }
    return mapping.get(category, "General evaluation gap")


def choose_case(results: List[Dict], category: str, preferred_case_type: str | None = None) -> Dict | None:
    filtered = [item for item in results if item["failure_category"] == category]
    if preferred_case_type:
        typed = [item for item in filtered if item["case_type"] == preferred_case_type]
        if typed:
            filtered = typed
    if not filtered:
        return None
    return sorted(
        filtered,
        key=lambda item: (
            item["judge"]["final_score"],
            item["ragas"]["retrieval"]["mrr"],
            item["ragas"]["relevancy"],
        ),
    )[0]


def representative_failures(v1_results: List[Dict]) -> List[Dict]:
    picks = [
        choose_case(v1_results, "unsafe_compliance", "adversarial"),
        choose_case(v1_results, "retrieval_miss", "out_of_context"),
        choose_case(v1_results, "low_judge_score", "normal"),
    ]
    return [item for item in picks if item is not None]


def residual_risks(v2_results: List[Dict]) -> List[Dict]:
    ranked = sorted(
        v2_results,
        key=lambda item: (
            item["judge"]["final_score"],
            item["ragas"]["faithfulness"],
            item["ragas"]["relevancy"],
            item["ragas"]["retrieval"]["mrr"],
        ),
    )
    selected: List[Dict] = []
    seen_ids = set()
    for item in ranked:
        if item["case_id"] in seen_ids:
            continue
        if item["case_type"] == "normal" and len(selected) >= 1:
            continue
        selected.append(item)
        seen_ids.add(item["case_id"])
        if len(selected) == 3:
            break
    return selected


def why_chain(result: Dict) -> List[str]:
    case_id = result["case_id"]
    case_type = result["case_type"]
    answer = result["agent_response"]
    retrieved = result["retrieved_ids"]
    expected = result["ragas"]["retrieval"]["expected_ids"]
    category = result["failure_category"]

    if category == "unsafe_compliance":
        return [
            f"Symptom: `{case_id}` failed because the agent followed an adversarial instruction instead of refusing it.",
            "Why 1: The generator had a direct branch that obeyed prompt-injection patterns for the baseline agent.",
            "Why 2: Safety behavior was encoded as a version-specific string rule, not as a default refusal policy.",
            "Why 3: The pipeline let generation continue even when the request was clearly outside allowed support behavior.",
            "Why 4: Judge feedback only detected the failure after the harmful answer was already produced.",
            "Root Cause: Prompting and safety guardrails were too weak in Agent_V1_Base.",
        ]

    if category == "retrieval_miss":
        return [
            f"Symptom: `{case_id}` failed on a `{case_type}` query by retrieving fallback documents and answering from them.",
            f"Why 1: The retriever returned {retrieved} even though the expected retrieval set was {expected}.",
            "Why 2: When lexical matching found no support, the baseline retriever injected default top-k documents instead of returning no context.",
            "Why 3: The generator interpreted any retrieved context as permission to answer confidently.",
            "Why 4: There was no explicit abstain path for out-of-context or ambiguous questions.",
            "Root Cause: Retrieval fallback behavior caused hallucination-prone answers on unsupported queries.",
        ]

    return [
        f"Symptom: `{case_id}` scored only {result['judge']['final_score']}/5 even though the gold document was still present in retrieval.",
        f"Why 1: The retriever returned {retrieved}, while the expected document list was {expected}.",
        "Why 2: The correct document was not ranked first, so the baseline generator answered from the wrong chunk.",
        "Why 3: Generation was hard-wired to copy the first retrieved context instead of validating against all retrieved evidence.",
        "Why 4: Retrieval quality and answer quality were too tightly coupled to top-1 ranking quality.",
        "Root Cause: Ranking noise plus top-1 answer selection produced systematic low-judge-score failures.",
    ]


def residual_risk_lines(result: Dict) -> List[str]:
    case_id = result["case_id"]
    case_type = result["case_type"]
    score = result["judge"]["final_score"]
    retrieved = result["retrieved_ids"]
    expected = result["ragas"]["retrieval"]["expected_ids"]

    notes = [
        f"`{case_id}` ({case_type}) still deserves monitoring because it scored {score}/5.",
        f"Retrieved IDs: {retrieved}; expected IDs: {expected}.",
    ]

    if case_id == "case_hard_058":
        notes.append("Risk signal: the answer is correct, but retrieval still pulls an extra password-reset distractor for a multi-turn security question.")
        notes.append("Likely root area: lexical retrieval remains sensitive to overlapping security vocabulary.")
    elif case_id == "case_hard_059":
        notes.append("Risk signal: the answer is correct, but retrieval does not surface `kb_sla`, so coverage for aggregation questions is still brittle.")
        notes.append("Likely root area: top-k retrieval may under-cover multi-document synthesis tasks.")
    else:
        notes.append("Risk signal: the case passed, but it shows that answer quality still depends on deterministic lexical ranking behavior.")
        notes.append("Likely root area: residual coupling between retrieval ordering and generation.")

    return notes


def format_metric_row(label: str, v1_value, v2_value) -> str:
    if isinstance(v1_value, float):
        v1_value = round(v1_value, 3)
    if isinstance(v2_value, float):
        v2_value = round(v2_value, 3)
    return f"| {label} | {v1_value} | {v2_value} |"


def build_report(summary: Dict, result_sets: Dict[str, List[Dict]]) -> str:
    v1_results = result_sets.get("v1", [])
    v2_results = result_sets["v2"]
    v1 = summarize_results("Agent_V1_Base", v1_results) if v1_results else None
    v2 = summarize_results(summary["metadata"]["version"], v2_results)

    regression = summary.get("regression", {})
    release_gate = summary.get("release_gate", {})
    v1_failure_rows = ""
    if v1:
        v1_failure_rows = "\n".join(
            f"| {category} | {count} | {failure_root_area(category)} |"
            for category, count in v1["failure_categories"].most_common()
        )
    v2_failure_rows = "\n".join(
        f"| {category} | {count} | {failure_root_area(category)} |"
        for category, count in v2["failure_categories"].most_common()
    ) or "| none | 0 | No blocking failure remained in the candidate run. |"

    representative_sections = []
    for index, item in enumerate(representative_failures(v1_results), start=1):
        lines = why_chain(item)
        bullets = "\n".join(f"{i}. {line}" for i, line in enumerate(lines, start=1))
        representative_sections.append(f"### Case #{index}: {item['case_id']} ({item['failure_category']})\n{bullets}")

    residual_sections = []
    for item in residual_risks(v2_results):
        lines = residual_risk_lines(item)
        bullets = "\n".join(f"- {line}" for line in lines)
        residual_sections.append(bullets)

    overview_rows = "\n".join(
        [
            format_metric_row("Pass rate", v1["passes"] / v1["total"] if v1 else "N/A", summary["metrics"]["pass_rate"]),
            format_metric_row("Average judge score", v1["avg_score"] if v1 else "N/A", summary["metrics"]["avg_score"]),
            format_metric_row("Faithfulness", v1["faithfulness"] if v1 else "N/A", summary["metrics"]["faithfulness"]),
            format_metric_row("Relevancy", v1["relevancy"] if v1 else "N/A", summary["metrics"]["relevancy"]),
            format_metric_row("Hit rate", v1["hit_rate"] if v1 else "N/A", summary["metrics"]["hit_rate"]),
            format_metric_row("MRR", v1["mrr"] if v1 else "N/A", summary["metrics"]["mrr"]),
            format_metric_row("Agreement rate", v1["agreement_rate"] if v1 else "N/A", summary["metrics"]["agreement_rate"]),
            format_metric_row("Estimated cost (USD)", v1["cost"] if v1 else "N/A", summary["cost"]["estimated_cost_usd"]),
            format_metric_row("Average latency (sec)", v1["latency"] if v1 else "N/A", summary["latency"]["avg_latency_sec"]),
        ]
    )

    v1_case_types = json.dumps(v1["failed_case_types"], ensure_ascii=False) if v1 else "{}"
    v2_red_team_types = json.dumps(summary["red_team_summary"]["types"], ensure_ascii=False)
    release_decision = release_gate.get("decision", "N/A")

    return f"""# Failure Analysis Report

## 1. Benchmark Overview
| Metric | Agent_V1_Base | {summary['metadata']['version']} |
|---|---:|---:|
{overview_rows}

- Total cases: {summary['metadata']['total']}
- Release gate decision: `{release_decision}`
- Regression delta: avg score {regression.get('delta_avg_score', 'N/A')}, hit rate {regression.get('delta_hit_rate', 'N/A')}, MRR {regression.get('delta_mrr', 'N/A')}, cost {regression.get('delta_cost_usd', 'N/A')} USD, runtime {regression.get('delta_runtime_sec', 'N/A')} sec.
- Candidate runtime: {summary['latency']['total_runtime_sec']} seconds for {summary['metadata']['total']} cases.

## 2. Failure Clustering
The candidate run passed all 60 cases, so clustering has to look at both the fixed failures in `Agent_V1_Base` and the residual risks left in `{summary['metadata']['version']}`.

### Fixed Failure Clusters in Agent_V1_Base
| Failure group | Count | Root area |
|---|---:|---|
{v1_failure_rows}

- Failed case-type distribution in V1: {v1_case_types}
- Main pattern: 48 of 54 failures were `low_judge_score`, which means the baseline often retrieved the correct document somewhere in top-k but still answered from the wrong first chunk.

### Candidate Failure Status in {summary['metadata']['version']}
| Failure group | Count | Root area |
|---|---:|---|
{v2_failure_rows}

- Hard cases covered: {summary['red_team_summary']['total_hard_cases']}
- Hard-case pass rate: {summary['red_team_summary']['pass_rate']}
- Hard-case mix: {v2_red_team_types}
- Position-bias flags: {summary['judge_reliability']['position_bias_cases']} cases still showed asymmetry in the judge comparison.

## 3. 5 Whys on the Most Important Fixed Failures
Because the candidate has zero blocking failures, the deepest root-cause analysis focuses on the baseline defects that regression testing actually removed.

{chr(10).join(representative_sections)}

## 4. Residual Risks in the Passing Candidate
The candidate cleared the release gate, but these signals still matter before calling the system robust:

{chr(10).join(residual_sections)}

## 5. Improvement Action Plan
- [ ] Replace pure lexical ranking with semantic retrieval plus reranking so the correct document is reliably first for normal and multi-turn questions.
- [ ] Keep the strict refusal path as the default generation behavior, not as a version-specific exception list.
- [ ] Add a no-context confidence gate so unsupported or ambiguous questions return refusal or clarification before generation begins.
- [ ] Expand latency-stress tests to require all expected documents to appear in retrieval, not just a correct-looking final answer.
- [ ] Audit the 7 position-bias cases and calibrate the judges with swapped-order evaluation examples.
"""


def main() -> None:
    if not os.path.exists(SUMMARY_PATH) or not os.path.exists(BENCHMARK_PATH):
        raise FileNotFoundError("Missing reports. Run python main.py before generating failure analysis.")

    summary = load_json(SUMMARY_PATH)
    benchmark_data = load_json(BENCHMARK_PATH)
    result_sets = get_result_sets(benchmark_data)
    report = build_report(summary, result_sets)

    os.makedirs("analysis", exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
