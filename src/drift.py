from __future__ import annotations

from pydantic import BaseModel
from src.models import EvalRun


DRIFT_THRESHOLD = 0.05   # flag slow drift if rolling avg drops 5% below peak


class DriftResult(BaseModel):
    window_size: int
    run_ids: list[str]
    accuracies: list[float]
    rolling_avg: float
    peak_accuracy: float
    delta_from_peak: float   # negative means accuracy dropped below peak
    is_drifting: bool
    message: str


def detect_drift(runs: list[EvalRun], threshold: float = DRIFT_THRESHOLD) -> DriftResult:
    accuracies = [r.accuracy for r in runs]
    run_ids    = [r.run_id   for r in runs]

    rolling_avg    = round(sum(accuracies) / len(accuracies), 4)
    peak_accuracy  = max(accuracies)
    delta_from_peak = round(rolling_avg - peak_accuracy, 4)
    is_drifting    = delta_from_peak <= -threshold

    if is_drifting:
        message = (
            f"Slow drift detected over {len(runs)} runs: "
            f"rolling avg {rolling_avg:.1%} is {abs(delta_from_peak):.1%} below peak {peak_accuracy:.1%}."
        )
    else:
        message = (
            f"No drift detected over {len(runs)} runs: "
            f"rolling avg {rolling_avg:.1%}, peak {peak_accuracy:.1%}."
        )

    return DriftResult(
        window_size=len(runs),
        run_ids=run_ids,
        accuracies=accuracies,
        rolling_avg=rolling_avg,
        peak_accuracy=peak_accuracy,
        delta_from_peak=delta_from_peak,
        is_drifting=is_drifting,
        message=message,
    )
