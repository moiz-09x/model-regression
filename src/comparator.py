from __future__ import annotations

import json
from pathlib import Path

from src.models import EvalDiff, EvalRun

RUNS_DIR = Path("data/runs")
WARNING_THRESHOLD = 0.06   # 6% drop — calibrated above observed LLM non-determinism noise (~5%)
CRITICAL_THRESHOLD = 0.12  # 12% drop — clearly a real regression, not noise


def load_run(run_id: str) -> EvalRun:
    path = RUNS_DIR / f"run_{run_id}.json"
    with open(path) as f:
        return EvalRun(**json.load(f))


def load_latest_runs(n: int = 2) -> list[EvalRun]:
    paths = sorted(RUNS_DIR.glob("run_*.json"))
    if len(paths) < n:
        return [EvalRun(**json.loads(p.read_text())) for p in paths]
    return [EvalRun(**json.loads(p.read_text())) for p in paths[-n:]]


def compare(baseline: EvalRun, current: EvalRun) -> EvalDiff:
    accuracy_delta = current.accuracy - baseline.accuracy
    summary_delta = current.avg_summary_score - baseline.avg_summary_score

    # Build lookup: test_case_id → passed (bool) for each run
    baseline_passed = {r.test_case_id: r.category_match for r in baseline.case_results}
    current_passed  = {r.test_case_id: r.category_match for r in current.case_results}

    regressions  = [id for id, passed in current_passed.items()  if not passed and baseline_passed.get(id)]
    improvements = [id for id, passed in current_passed.items()  if passed  and not baseline_passed.get(id)]

    categories = ["billing", "technical", "account", "general", "out_of_scope"]
    per_category_delta = {
        cat: round(current.accuracy_for_category(cat) - baseline.accuracy_for_category(cat), 4)
        for cat in categories
    }

    drop = -accuracy_delta  # positive means accuracy dropped
    if drop >= CRITICAL_THRESHOLD:
        status = "critical"
    elif drop >= WARNING_THRESHOLD:
        status = "warning"
    else:
        status = "pass"

    return EvalDiff(
        baseline_run_id=baseline.run_id,
        current_run_id=current.run_id,
        accuracy_delta=round(accuracy_delta, 4),
        summary_score_delta=round(summary_delta, 2),
        status=status,
        regressions=sorted(regressions),
        improvements=sorted(improvements),
        per_category_delta=per_category_delta,
    )


def print_diff(diff: EvalDiff) -> None:
    status_icon = {"pass": "✓", "warning": "⚠", "critical": "✗"}[diff.status]
    print(f"\n{status_icon}  Status: {diff.status.upper()}")
    print(f"   Accuracy delta : {diff.accuracy_delta:+.1%}")
    print(f"   Summary delta  : {diff.summary_score_delta:+.2f}/5")

    if diff.regressions:
        print(f"\n   Regressions ({len(diff.regressions)}):")
        for id in diff.regressions:
            print(f"     - {id}")

    if diff.improvements:
        print(f"\n   Improvements ({len(diff.improvements)}):")
        for id in diff.improvements:
            print(f"     + {id}")

    print("\n   Per-category accuracy delta:")
    for cat, delta in diff.per_category_delta.items():
        print(f"     {cat:12s}: {delta:+.1%}")
