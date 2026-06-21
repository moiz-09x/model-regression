import sys
from dotenv import load_dotenv
load_dotenv()

from src.evaluator import run_eval
from src.comparator import compare, load_latest_runs, print_diff
from src.drift import detect_drift
from src.reporter import generate_report
from src.alerting import build_slack_payload, send_slack_alert

run = run_eval(
    prompt_path="prompts/support_classifier_v1.1.yaml",
    dataset_path="data/golden_dataset_v1.2.json",
)

runs = load_latest_runs(n=7)

# Only compare runs on the same dataset version — cross-version comparisons are apples to oranges
same_dataset_runs = [r for r in runs if r.dataset_version == run.dataset_version]

diff  = compare(baseline=runs[-2], current=runs[-1]) if len(runs) >= 2 else None
drift = detect_drift(same_dataset_runs) if len(same_dataset_runs) >= 2 else None

if diff:
    print_diff(diff)

if drift:
    print(f"\n{drift.message}")

report_path = generate_report(run=run, diff=diff, drift=drift, all_runs=same_dataset_runs)

if diff:
    payload = build_slack_payload(run, diff, drift, str(report_path.resolve()))
    send_slack_alert(payload)

# Exit non-zero on critical regression so GitHub Actions blocks the PR merge
if diff and diff.status == "critical":
    print("\nCritical regression detected — blocking merge.", file=sys.stderr)
    sys.exit(1)
