from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from src.classifier import classify_email, load_prompt
from src.models import CaseResult, EvalRun, GoldenDataset, PromptConfig, TestCase
from src.scorer import score_summary

RUNS_DIR = Path("data/runs")


def load_dataset(path: str | Path) -> GoldenDataset:
    with open(path) as f:
        data = json.load(f)
    return GoldenDataset(**data)


def _evaluate_case(test_case: TestCase, prompt: PromptConfig, model: str) -> CaseResult:
    try:
        result = classify_email(test_case.email, prompt, model=model)
        summary_score = score_summary(
            email=test_case.email,
            expected_summary=test_case.expected_summary,
            actual_summary=result.output.summary,
        )
        return CaseResult(
            test_case_id=test_case.id,
            difficulty=test_case.difficulty,
            expected_category=test_case.expected_category,
            actual_category=result.output.category,
            category_match=result.output.category == test_case.expected_category,
            expected_summary=test_case.expected_summary,
            actual_summary=result.output.summary,
            summary_score=summary_score,
            latency_ms=result.latency_ms,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
    except Exception as e:
        # Classifier failed entirely even after retries — record the failure, don't crash the run
        return CaseResult(
            test_case_id=test_case.id,
            difficulty=test_case.difficulty,
            expected_category=test_case.expected_category,
            actual_category="general",   # safe default so the field is never empty
            category_match=False,
            expected_summary=test_case.expected_summary,
            actual_summary="",
            summary_score=1,
            latency_ms=0.0,
            input_tokens=0,
            output_tokens=0,
            error=str(e),
        )


def run_eval(
    prompt_path: str | Path,
    dataset_path: str | Path,
    model: str = "deepseek-v4-flash",
    max_workers: int = 5,
) -> EvalRun:
    prompt = load_prompt(prompt_path)
    dataset = load_dataset(dataset_path)

    print(f"Running eval: prompt={prompt.version}, dataset={dataset.version}, cases={len(dataset.test_cases)}")

    case_results: list[CaseResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_evaluate_case, tc, prompt, model): tc
            for tc in dataset.test_cases
        }
        for future in as_completed(futures):
            tc = futures[future]
            result = future.result()
            status = "PASS" if result.category_match else "FAIL"
            print(f"  [{status}] {tc.id} — expected={result.expected_category}, got={result.actual_category}, summary_score={result.summary_score}/5")
            case_results.append(result)

    # Sort by test case ID so the output file is deterministic
    case_results.sort(key=lambda r: r.test_case_id)

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + f"_{prompt.version}"
    eval_run = EvalRun(
        run_id=run_id,
        prompt_version=prompt.version,
        dataset_version=dataset.version,
        model=model,
        timestamp=datetime.utcnow().isoformat(),
        case_results=case_results,
    )

    _save_run(eval_run)
    return eval_run


def _save_run(run: EvalRun) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"run_{run.run_id}.json"
    with open(path, "w") as f:
        f.write(run.model_dump_json(indent=2))
    print(f"\nRun saved: {path}")
    print(f"Accuracy: {run.accuracy:.1%} ({run.passed_cases}/{run.total_cases})")
    print(f"Avg summary score: {run.avg_summary_score}/5")
    print(f"Avg latency: {run.avg_latency_ms}ms | Total tokens: {run.total_tokens}")
    return path
