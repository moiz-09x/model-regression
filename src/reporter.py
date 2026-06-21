from __future__ import annotations

from pathlib import Path
from src.models import EvalDiff, EvalRun
from src.drift import DriftResult

REPORTS_DIR = Path("reports")


def generate_report(
    run: EvalRun,
    diff: EvalDiff | None,
    drift: DriftResult | None,
    all_runs: list[EvalRun],
) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)
    path = REPORTS_DIR / f"report_{run.run_id}.html"
    path.write_text(_render(run, diff, drift, all_runs))
    print(f"Report generated: {path}")

    summary_path = REPORTS_DIR / "summary.md"
    summary_path.write_text(_markdown_summary(run, diff, drift))

    return path


def _markdown_summary(run: EvalRun, diff: EvalDiff | None, drift: DriftResult | None) -> str:
    status = diff.status if diff else "pass"
    icon = {"pass": "✓", "warning": "⚠", "critical": "✗"}[status]

    acc_delta   = f" ({diff.accuracy_delta:+.1%} vs baseline)" if diff else ""
    score_delta = f" ({diff.summary_score_delta:+.2f} vs baseline)" if diff else ""

    lines = [
        f"## Eval — {status.upper()} {icon}",
        "",
        f"| | |",
        f"|---|---|",
        f"| Accuracy | **{run.accuracy:.1%}**{acc_delta} |",
        f"| Summary score | {run.avg_summary_score}/5{score_delta} |",
        f"| Avg latency | {run.avg_latency_ms:.0f}ms |",
        f"| Tokens | {run.total_tokens:,} ({run.total_cases} cases) |",
        f"| Prompt | `{run.prompt_version}` |",
        f"| Dataset | `{run.dataset_version}` |",
        "",
    ]

    if diff and diff.regressions:
        lines.append(f"### Regressions ({len(diff.regressions)})")
        lines.append("")
        lines.append("| Case | Expected | Got |")
        lines.append("|------|----------|-----|")
        reg_ids = set(diff.regressions)
        for r in run.case_results:
            if r.test_case_id in reg_ids:
                lines.append(f"| `{r.test_case_id}` | {r.expected_category} | **{r.actual_category}** |")
        lines.append("")
    else:
        lines.append("No regressions detected.")
        lines.append("")

    if diff and diff.improvements:
        lines.append(f"### Improvements ({len(diff.improvements)}): " + ", ".join(f"`{id}`" for id in diff.improvements))
        lines.append("")

    if drift and drift.is_drifting:
        lines.append(f"> ⚠ **Drift:** {drift.message}")
        lines.append("")

    return "\n".join(lines)


def _render(run: EvalRun, diff: EvalDiff | None, drift: DriftResult | None, all_runs: list[EvalRun]) -> str:
    status = diff.status if diff else "pass"
    status_label = {"pass": "PASS", "warning": "WARNING", "critical": "CRITICAL"}[status]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Eval — {run.run_id}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
          font-size: 14px; line-height: 1.6; color: #111; background: #fff; }}
  .wrap {{ max-width: 880px; margin: 0 auto; padding: 48px 24px; }}

  .status-line {{ font-size: 13px; color: #555; margin-bottom: 32px; }}
  .status-line strong {{ color: #111; }}

  h1 {{ font-size: 22px; font-weight: 600; margin-bottom: 4px; }}
  h2 {{ font-size: 13px; font-weight: 600; text-transform: uppercase;
        letter-spacing: .06em; color: #555; margin: 40px 0 12px; }}

  .scorecard {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px;
                background: #e5e5e5; border: 1px solid #e5e5e5; margin-bottom: 40px; }}
  .metric {{ background: #fff; padding: 16px; }}
  .metric .label {{ font-size: 11px; color: #888; text-transform: uppercase;
                    letter-spacing: .05em; margin-bottom: 6px; }}
  .metric .val {{ font-size: 24px; font-weight: 600; }}
  .metric .sub {{ font-size: 12px; color: #888; margin-top: 2px; }}
  .up {{ color: #16a34a; }} .down {{ color: #dc2626; }}

  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 12px; font-size: 11px; font-weight: 600;
        text-transform: uppercase; letter-spacing: .05em; color: #888;
        border-bottom: 1px solid #e5e5e5; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
  tr.fail td {{ background: #fafafa; }}
  .fail-marker {{ color: #dc2626; font-weight: 600; }}
  .pass-marker {{ color: #16a34a; }}

  .notice {{ padding: 12px 16px; border-left: 3px solid #e5e5e5;
             color: #555; font-size: 13px; margin-bottom: 24px; }}
  .notice.warn {{ border-color: #f59e0b; }}

  .trend {{ display: flex; align-items: flex-end; gap: 3px; height: 48px; margin-top: 12px; }}
  .bar {{ flex: 1; background: #111; border-radius: 2px 2px 0 0; min-height: 2px; }}
  .trend-labels {{ display: flex; justify-content: space-between;
                   font-size: 11px; color: #aaa; margin-top: 4px; }}

  .meta {{ font-size: 12px; color: #555; margin-top: 48px; padding-top: 24px;
           border-top: 1px solid #e5e5e5; }}
  .meta dt {{ color: #aaa; float: left; width: 140px; }}
  .meta dd {{ margin-left: 140px; margin-bottom: 4px; font-family: monospace; }}
</style>
</head>
<body>
<div class="wrap">

  <h1>{status_label}</h1>
  <div class="status-line">
    <strong>{run.prompt_version}</strong> &nbsp;/&nbsp;
    <strong>{run.dataset_version}</strong> &nbsp;·&nbsp;
    {run.model} &nbsp;·&nbsp;
    {run.timestamp[:19].replace("T", " ")} UTC
  </div>

  {_scorecard(run, diff)}

  {_drift_notice(drift) if drift else ""}

  {_trend(all_runs) if len(all_runs) >= 2 else ""}

  {_regression_section(run, diff) if diff else ""}

  {_results_table(run)}

  {_metadata(run, diff)}

</div>
</body>
</html>"""


def _delta(val: float, fmt: str = ".1%") -> str:
    if val == 0:
        return f'<span class="sub">no change</span>'
    cls = "up" if val > 0 else "down"
    sign = "+" if val > 0 else ""
    return f'<span class="{cls}">{sign}{val:{fmt}} vs baseline</span>'


def _scorecard(run: EvalRun, diff: EvalDiff | None) -> str:
    acc_d   = _delta(diff.accuracy_delta)        if diff else '<span class="sub">first run</span>'
    score_d = _delta(diff.summary_score_delta, ".2f") if diff else '<span class="sub">first run</span>'
    return f"""
  <div class="scorecard">
    <div class="metric">
      <div class="label">Accuracy</div>
      <div class="val">{run.accuracy:.1%}</div>
      <div class="sub">{acc_d}</div>
    </div>
    <div class="metric">
      <div class="label">Summary Score</div>
      <div class="val">{run.avg_summary_score}<span style="font-size:14px;font-weight:400">/5</span></div>
      <div class="sub">{score_d}</div>
    </div>
    <div class="metric">
      <div class="label">Avg Latency</div>
      <div class="val">{run.avg_latency_ms:.0f}<span style="font-size:14px;font-weight:400">ms</span></div>
      <div class="sub">per request</div>
    </div>
    <div class="metric">
      <div class="label">Tokens Used</div>
      <div class="val">{run.total_tokens:,}</div>
      <div class="sub">{run.total_cases} cases</div>
    </div>
  </div>"""


def _drift_notice(drift: DriftResult) -> str:
    if drift.is_drifting:
        return f'<div class="notice warn">{drift.message}</div>'
    return f'<div class="notice">{drift.message}</div>'


def _trend(runs: list[EvalRun]) -> str:
    W, H = 800, 120
    pad_l, pad_r, pad_t, pad_b = 44, 16, 12, 28
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b

    accuracies = [r.accuracy for r in runs]
    lo = max(0.0, min(accuracies) - 0.05)
    hi = min(1.0, max(accuracies) + 0.05)
    span = hi - lo or 0.1

    def x(i):  return pad_l + (i / max(len(runs) - 1, 1)) * plot_w
    def y(acc): return pad_t + (1 - (acc - lo) / span) * plot_h

    points = " ".join(f"{x(i):.1f},{y(a):.1f}" for i, a in enumerate(accuracies))

    # y-axis gridlines at 25% intervals within the visible range
    grid = ""
    for pct in [lo + span * t for t in [0, 0.25, 0.5, 0.75, 1.0]]:
        yy = y(pct)
        grid += f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{W - pad_r}" y2="{yy:.1f}" stroke="#f0f0f0" stroke-width="1"/>'
        grid += f'<text x="{pad_l - 6}" y="{yy + 4:.1f}" text-anchor="end" font-size="10" fill="#aaa">{pct:.0%}</text>'

    # dots with tooltips
    dots = ""
    for i, r in enumerate(runs):
        label = f"{r.accuracy:.1%} — {r.run_id[:20]}"
        dots += (
            f'<circle cx="{x(i):.1f}" cy="{y(r.accuracy):.1f}" r="4" fill="#111">'
            f'<title>{label}</title></circle>'
        )

    # x-axis labels: first and last only to avoid crowding
    x_labels = (
        f'<text x="{x(0):.1f}" y="{H}" text-anchor="start" font-size="10" fill="#aaa">{runs[0].run_id[:16]}</text>'
        f'<text x="{x(len(runs)-1):.1f}" y="{H}" text-anchor="end" font-size="10" fill="#aaa">{runs[-1].run_id[:16]}</text>'
    )

    svg = f"""<svg viewBox="0 0 {W} {H}" style="width:100%;overflow:visible" xmlns="http://www.w3.org/2000/svg">
    {grid}
    <polyline points="{points}" fill="none" stroke="#111" stroke-width="1.5"/>
    {dots}
    {x_labels}
  </svg>"""

    return f"""
  <h2>Accuracy trend ({len(runs)} runs)</h2>
  <div style="margin-bottom:40px">{svg}</div>"""


def _regression_section(run: EvalRun, diff: EvalDiff) -> str:
    if not diff.regressions:
        return '<div class="notice" style="margin-top:24px">No regressions in this run.</div>'

    reg_ids = set(diff.regressions)
    rows = "".join(
        f"""<tr class="fail">
          <td><code>{r.test_case_id}</code></td>
          <td>{r.difficulty}</td>
          <td>{r.expected_category}</td>
          <td class="fail-marker">{r.actual_category}</td>
          <td>{r.expected_summary}</td>
          <td>{r.actual_summary}</td>
        </tr>"""
        for r in run.case_results if r.test_case_id in reg_ids
    )
    return f"""
  <h2>Regressions ({len(diff.regressions)})</h2>
  <table>
    <thead><tr><th>ID</th><th>Difficulty</th><th>Expected</th><th>Got</th>
    <th>Expected Summary</th><th>Actual Summary</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>"""


def _results_table(run: EvalRun) -> str:
    rows = "".join(
        f"""<tr class="{'fail' if not r.category_match else ''}">
          <td><code>{r.test_case_id}</code></td>
          <td>{'<span class="fail-marker">FAIL</span>' if not r.category_match else '<span class="pass-marker">pass</span>'}</td>
          <td>{r.expected_category}</td>
          <td>{r.actual_category if not r.category_match else '—'}</td>
          <td>{r.actual_summary}</td>
          <td>{r.summary_score}/5</td>
        </tr>"""
        for r in sorted(run.case_results, key=lambda x: x.test_case_id)
    )
    return f"""
  <h2>All results</h2>
  <table>
    <thead><tr><th>ID</th><th>Status</th><th>Expected</th><th>Got</th>
    <th>Summary</th><th>Score</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>"""


def _metadata(run: EvalRun, diff: EvalDiff | None) -> str:
    baseline = diff.baseline_run_id if diff else "—"
    return f"""
  <dl class="meta">
    <dt>Run ID</dt>       <dd>{run.run_id}</dd>
    <dt>Baseline</dt>     <dd>{baseline}</dd>
    <dt>Prompt</dt>       <dd>{run.prompt_version}</dd>
    <dt>Dataset</dt>      <dd>{run.dataset_version}</dd>
    <dt>Model</dt>        <dd>{run.model}</dd>
    <dt>Timestamp</dt>    <dd>{run.timestamp}</dd>
  </dl>"""
