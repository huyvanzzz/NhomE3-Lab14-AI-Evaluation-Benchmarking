import json
import os


def validate_lab():
    print("[CHECK] Validating submission format...")

    required_files = [
        "reports/summary.json",
        "reports/benchmark_results.json",
        "analysis/failure_analysis.md",
    ]

    missing = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"[OK] Found: {file_path}")
        else:
            print(f"[ERROR] Missing file: {file_path}")
            missing.append(file_path)

    if missing:
        print(f"\n[ERROR] Missing {len(missing)} required files. Add them before submission.")
        return False

    try:
        with open("reports/summary.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as error:
        print(f"[ERROR] reports/summary.json is not valid JSON: {error}")
        return False

    if "metrics" not in data or "metadata" not in data:
        print("[ERROR] summary.json must contain 'metrics' and 'metadata'.")
        return False

    metrics = data["metrics"]
    print("\n--- Quick stats ---")
    print(f"Total cases: {data['metadata'].get('total', 'N/A')}")
    print(f"Average score: {metrics.get('avg_score', 0):.2f}")

    has_retrieval = "hit_rate" in metrics and "mrr" in metrics
    if has_retrieval:
        print(f"[OK] Retrieval metrics found (Hit Rate: {metrics['hit_rate'] * 100:.1f}%, MRR: {metrics['mrr']:.2f})")
    else:
        print("[WARN] Missing retrieval metrics: hit_rate and/or mrr.")

    has_multi_judge = "agreement_rate" in metrics
    if has_multi_judge:
        print(f"[OK] Multi-judge metrics found (Agreement Rate: {metrics['agreement_rate'] * 100:.1f}%)")
    else:
        print("[WARN] Missing multi-judge metric: agreement_rate.")

    if "regression" in data and "release_gate" in data:
        print(f"[OK] Regression and release gate found ({data['release_gate'].get('decision', 'N/A')})")
    else:
        print("[WARN] Missing regression or release gate section.")

    if data["metadata"].get("version"):
        print("[OK] Agent version metadata found.")

    print("\n[READY] Lab submission is ready for grading.")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if validate_lab() else 1)
