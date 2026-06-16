# Failure Analysis Report

## 1. Executive Summary
This report summarizes the benchmark result and failure analysis for the Lab Day 14 AI Evaluation Factory. The system evaluates two agent versions on the same golden dataset:

- `Agent_V1_Base`: baseline version for regression comparison.
- `Agent_V2_Optimized`: candidate version for release decision.

The latest benchmark uses 52 golden test cases. This satisfies the rubric requirement of 50+ cases. The candidate version passed all 52 cases and the release gate returned `APPROVE`.

Main conclusion: `Agent_V2_Optimized` is ready for submission because it keeps retrieval quality high, improves ranking quality, improves judge score, reduces cost, and runs far below the 2-minute performance target.

## 2. Benchmark Scope and Pipeline
The benchmark is designed for a RAG-style evaluation pipeline. It does not only check the final answer; it also separates retrieval, answer quality, judge reliability, regression, cost, and performance.

Each golden test case contains:

- `question`: user query.
- `expected_answer`: expected ground-truth answer.
- `context`: source context used to answer.
- `expected_retrieval_ids`: ground-truth document IDs for retrieval evaluation.
- `metadata`: difficulty and case type.

Evaluation flow:

1. The agent answers the test question.
2. The retrieval evaluator compares `expected_retrieval_ids` with `retrieved_ids`.
3. Answer quality is scored with faithfulness, relevancy, answer overlap, and refusal correctness.
4. Multi-judge scoring produces final score, agreement rate, Cohen's Kappa, and conflict flags.
5. Regression logic compares V1 and V2.
6. Release gate decides `APPROVE` or `BLOCK_RELEASE`.

## 3. Benchmark Overview
Latest candidate summary from `reports/summary.json`:

| Metric | Agent_V2_Optimized |
|---|---:|
| Total cases | 52 |
| Pass/Fail | 52/0 |
| Pass rate | 1.0 |
| Average judge score | 5.0 / 5.0 |
| Faithfulness | 0.766 |
| Relevancy | 1.0 |
| Retrieval Hit Rate | 1.0 |
| Retrieval MRR | 1.0 |
| Multi-Judge Agreement Rate | 1.0 |
| Cohen's Kappa | 1.0 |
| Total runtime | 0.281 seconds |
| Average latency | 0.046 seconds |
| P95 latency | 0.048 seconds |
| Cases per second | 185.01 |
| Total tokens | 4501 |
| Average tokens per case | 86.56 |
| Estimated total cost | $0.009002 |
| Average cost per case | $0.000173 |

Regression deltas from V1 to V2:

| Delta metric | Value |
|---|---:|
| Average score delta | +2.212 |
| Hit Rate delta | +0.0 |
| MRR delta | +0.552 |
| Cost delta | -0.00445 USD |
| Runtime delta | -0.172 seconds |

Interpretation:

- V2 preserves perfect retrieval coverage.
- V2 improves MRR by 0.552, so correct documents are ranked much higher.
- V2 improves average judge score by 2.212 points.
- V2 reduces both runtime and estimated cost.
- V2 passes every release gate check.

## 4. Dataset and Red-Team Coverage
The dataset contains 52 cases. It is not limited to simple fact-checking; it also includes adversarial, edge-case, and multi-turn examples.

| Case type | Count | Purpose |
|---|---:|---|
| fact-check | 15 | Validate normal factual policy QA |
| adversarial | 12 | Test prompt injection, goal hijacking, and unsafe requests |
| edge-case | 12 | Test ambiguity, unsupported context, and unusual inputs |
| multi-turn | 13 | Test follow-up questions and context carry-over |

Hard-case pass rate: 1.0.

This dataset design supports the rubric requirement for Dataset and SDG because it includes more than 50 cases, ground-truth retrieval IDs, and red-team style cases.

## 5. Retrieval Evaluation
Retrieval Evaluation is important because the agent follows a RAG-style workflow. If the retrieved context is wrong, the generated answer can be wrong even if the language model is strong.

### 5.1 Hit Rate
Hit Rate checks whether at least one expected document appears in the retrieved top-k list.

```text
Hit Rate = 1 if any expected_retrieval_id appears in retrieved_ids[:top_k], otherwise 0
```

Current result:

- Hit Rate = 1.0

This means every benchmark case retrieved at least one expected document.

### 5.2 MRR
MRR, or Mean Reciprocal Rank, measures how high the first correct document appears in the retrieved list.

```text
MRR = 1 / rank_of_first_correct_document
```

Examples:

- Correct document at rank 1 -> MRR = 1.0
- Correct document at rank 2 -> MRR = 0.5
- Correct document at rank 3 -> MRR = 0.333

Current result:

- MRR = 1.0

This means the first correct document is ranked first in the candidate run.

### 5.3 Retrieval Quality vs Answer Quality
Hit Rate alone is not enough. A retriever can include the correct document somewhere in top-k but still place it below distractor documents. In that case, answer generation may use the wrong top-ranked context. MRR helps reveal this ranking problem.

The regression result shows this clearly: V2 keeps Hit Rate high and improves MRR by 0.552. This ranking improvement is a major reason why V2 reaches a perfect pass rate.

## 6. Multi-Judge Consensus
The evaluation uses a multi-judge style output. The goal is to reduce dependence on a single judge score.

Current candidate judge metrics:

| Metric | Value |
|---|---:|
| Agreement Rate | 1.0 |
| Cohen's Kappa | 1.0 |
| Position-bias cases | 0 |

Interpretation:

- Agreement Rate = 1.0 means the judge outputs agree on the candidate run.
- Cohen's Kappa = 1.0 means agreement remains perfect after accounting for chance agreement.
- Position-bias cases = 0 means no position-bias signal was detected in this run.

Residual concern: the current judge is deterministic/offline, so future production-like evaluation should add optional real LLM judges for disputed or low-confidence cases.

## 7. Regression Testing and Release Gate
Release gate thresholds:

| Check | Threshold | Candidate result | Status |
|---|---:|---:|---|
| Average score not regressed | V2 >= V1 | +2.212 delta | Pass |
| Hit Rate | >= 0.80 | 1.0 | Pass |
| MRR | >= 0.60 | 1.0 | Pass |
| Agreement Rate | >= 0.70 | 1.0 | Pass |
| Cost increase | <= 30% | -33.1% | Pass |

Release gate decision: `APPROVE`.

The release gate is strict because all checks must pass at the same time. This avoids approving a candidate that improves one metric but regresses in retrieval quality, judge reliability, or cost.

## 8. Performance, Token, and Cost Analysis
The benchmark runner uses asynchronous batch execution.

| Performance metric | Value |
|---|---:|
| Total runtime | 0.281 seconds |
| Average latency | 0.046 seconds |
| P95 latency | 0.048 seconds |
| Cases per second | 185.01 |
| Batch size | 10 |

| Cost metric | Value |
|---|---:|
| Total tokens | 4501 |
| Average tokens per case | 86.56 |
| Estimated total cost | $0.009002 |
| Average cost per case | $0.000173 |

This satisfies the Performance Async requirement because the full benchmark runs far below 2 minutes for 50+ cases.

Cost reduction plan:

- Cache retrieval results for repeated or similar questions.
- Use offline judges as a first-pass filter.
- Send only failed, low-confidence, or judge-disagreement cases to real LLM judges.
- Trim unnecessary context before judge scoring.
- Keep async batching to reduce wall-clock runtime.

## 9. Failure Clustering
The candidate run has zero failed cases.

| Failure group | Count | Meaning |
|---|---:|---|
| retrieval_miss | 0 | Required documents were retrieved |
| unsafe_compliance | 0 | Adversarial cases did not trigger unsafe behavior |
| ambiguity_handling | 0 | Edge cases did not fail the judge threshold |
| hallucination | 0 | No unsupported-answer failure was detected |
| low_judge_score | 0 | No answer fell below the pass threshold |

Because V2 has no blocking failures, the failure analysis focuses on residual risks that should be monitored in future runs.

## 10. 5 Whys Residual Risk Analysis

### Case Group 1: Multi-turn Context Carry-over
1. Symptom: Multi-turn cases pass, but follow-up questions are still risky.
2. Why 1: Follow-up questions can omit important context.
3. Why 2: Retrieval may rely on surface tokens instead of full conversation meaning.
4. Why 3: The current agent is deterministic and benchmark-oriented.
5. Why 4: A real production agent would need stronger memory and semantic retrieval.
6. Root Cause: Multi-turn robustness requires better context tracking and semantic reranking.

### Case Group 2: Edge Cases and Ambiguity
1. Symptom: Edge cases pass, but unsupported or ambiguous questions remain a common RAG failure mode.
2. Why 1: Users may ask questions that are not covered by documentation.
3. Why 2: If the system retrieves fallback context, generation may answer with weak grounding.
4. Why 3: A confidence gate is needed before generation.
5. Why 4: Without an abstain path, unsupported questions can become hallucinations.
6. Root Cause: The system needs stronger no-context and clarification logic for unseen data.

### Case Group 3: Adversarial Prompt Injection
1. Symptom: Adversarial cases pass, but prompt injection is still a high-risk category.
2. Why 1: Users may ask the agent to ignore previous instructions.
3. Why 2: If refusal logic is weak, the agent may follow the malicious instruction.
4. Why 3: Safety should be enforced before generation, not only judged after generation.
5. Why 4: Judge scoring can detect unsafe behavior, but detection is not prevention.
6. Root Cause: Prompt-injection resistance should be a default guardrail in the agent design.

## 11. Action Plan
| Priority | Action | Expected benefit |
|---|---|---|
| High | Add semantic retrieval or reranking | Improve robustness on ambiguous and multi-turn cases |
| High | Add a no-context confidence gate | Reduce hallucination risk on unsupported questions |
| High | Keep strict refusal behavior for adversarial prompts | Improve safety |
| Medium | Add more conflicting-information cases | Better policy reasoning coverage |
| Medium | Add optional real LLM judge for disputed cases | Stronger multi-judge reliability |
| Medium | Measure token usage by stage | Better cost optimization |
| Low | Add test case IDs explicitly to all generated cases | Easier case-level debugging |

## 12. Final Conclusion
The current benchmark run is ready for submission. It satisfies the key group-level rubric requirements:

- Golden dataset with 50+ cases.
- Retrieval Evaluation with Hit Rate and MRR.
- Multi-Judge Consensus metrics.
- Regression Testing between V1 and V2.
- Release Gate logic.
- Async performance and cost tracking.
- Failure analysis with residual risk review.

The main future improvements are semantic retrieval, reranking, stronger no-context refusal logic, and optional real LLM judge escalation for disputed cases.
