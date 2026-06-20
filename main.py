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

diff  = compare(baseline=runs[-2], current=runs[-1]) if len(runs) >= 2 else None
drift = detect_drift(runs) if len(runs) >= 2 else None

if diff:
    print_diff(diff)

if drift:
    print(f"\n{drift.message}")

report_path = generate_report(run=run, diff=diff, drift=drift, all_runs=runs)

if diff:
    payload = build_slack_payload(run, diff, drift, str(report_path.resolve()))
    send_slack_alert(payload)
