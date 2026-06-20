from __future__ import annotations

import json
import os
from src.models import EvalDiff, EvalRun
from src.drift import DriftResult


def build_slack_payload(run: EvalRun, diff: EvalDiff, drift: DriftResult, report_path: str) -> dict:
    status_emoji = {"pass": ":white_check_mark:", "warning": ":warning:", "critical": ":x:"}
    emoji = status_emoji[diff.status]

    regression_lines = "\n".join(f"  • {id}" for id in diff.regressions) or "  None"
    drift_line = f":rotating_light: {drift.message}" if drift.is_drifting else f":chart_with_upwards_trend: {drift.message}"

    return {
        "text": f"{emoji} *Eval Run: {diff.status.upper()}* — prompt `{run.prompt_version}` / dataset `{run.dataset_version}`",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Eval {diff.status.upper()}: {run.prompt_version} / {run.dataset_version}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Accuracy*\n{run.accuracy:.1%} ({diff.accuracy_delta:+.1%})"},
                    {"type": "mrkdwn", "text": f"*Avg Summary Score*\n{run.avg_summary_score}/5 ({diff.summary_score_delta:+.2f})"},
                    {"type": "mrkdwn", "text": f"*Regressions*\n{len(diff.regressions)}"},
                    {"type": "mrkdwn", "text": f"*Improvements*\n{len(diff.improvements)}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Regressed cases:*\n{regression_lines}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": drift_line},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f":page_facing_up: <file://{report_path}|View full diff report>"},
            },
        ],
    }


def send_slack_alert(payload: dict) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("[alerting] SLACK_WEBHOOK_URL not set — skipping Slack notification.")
        print("[alerting] Payload that would have been sent:")
        print(json.dumps(payload, indent=2))
        return

    import urllib.request
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(webhook_url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        print(f"[alerting] Slack alert sent — HTTP {resp.status}")
