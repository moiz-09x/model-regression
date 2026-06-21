# Model Regression Detection System

A CI/CD pipeline that continuously tests LLM-powered features against a human-labeled golden dataset, detects quality regressions across prompt or model changes, and alerts before bad outputs reach users. It treats prompt changes the same way engineers treat code changes: tested, diffed, and gated before shipping.

---

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your DEEPSEEK_API_KEY
```

Run a full eval:

```bash
python main.py
```

This runs all 36 test cases through the classifier, scores each one, saves the run to `data/runs/`, generates an HTML report in `reports/`, and diffs against the previous run. On the first run there is no baseline to diff against — that's expected.

---

## Project structure

```
prompts/              Versioned prompt YAML files — this is the code under test
data/
  golden_dataset_v*.json   Hand-labeled test cases (ground truth)
  runs/                    Saved eval run results (one JSON file per run)
src/
  classifier.py     LLM feature being evaluated
  evaluator.py      Test runner — executes all cases, collects results
  scorer.py         LLM-as-judge for summary quality scoring (1–5)
  comparator.py     Diffs two runs, computes accuracy delta and regression list
  drift.py          Rolling average drift detection across run history
  reporter.py       HTML report generation
  alerting.py       Slack webhook alerting
  models.py         Pydantic data models shared across the pipeline
reports/            Generated HTML reports (gitignored except sample_report.html)
.github/workflows/  GitHub Actions eval pipeline
```

---

## Adding test cases

Test cases live in `data/golden_dataset_v*.json`. When you need to add cases:

1. **Create a new dataset version** — copy the latest file to `golden_dataset_vX.Y.json` and increment the version field inside. Never edit an existing version that has been used in a run; historical run files reference it by name and mutating it corrupts the audit trail.

2. **Write the case** — each case needs an `id`, `email`, `expected_category`, `expected_summary`, `difficulty`, and `notes`. The notes field should explain why this case matters, not just describe it.

3. **Label it yourself** — do not use an LLM to generate expected outputs. The golden dataset is ground truth; if the labels come from the same model family you're testing, regressions become invisible.

4. **Update `main.py`** to point to the new dataset version, run the eval, and commit both the new dataset and the resulting run file.

Valid categories: `billing`, `technical`, `account`, `general`, `out_of_scope`.

---

## Adjusting thresholds

Thresholds live in `src/comparator.py`:

```python
WARNING_THRESHOLD = 0.06   # accuracy drop that triggers a warning
CRITICAL_THRESHOLD = 0.12  # accuracy drop that blocks merge
```

These are calibrated to sit above the observed non-determinism noise floor (~5% variance between identical runs on DeepSeek v4 Flash at temperature=0). If you switch models, run the same prompt/dataset pair 3–5 times and measure the variance before setting new thresholds. Setting thresholds below your noise floor causes the warning to fire on noise, which trains the team to ignore it.

The drift detection threshold lives in `src/drift.py`:

```python
DRIFT_THRESHOLD = 0.05   # rolling avg drop below peak that flags slow drift
```

---

## Switching prompt or dataset versions

The active versions are declared in `config.yaml`:

```yaml
prompt: prompts/support_classifier_v1.1.yaml
dataset: data/golden_dataset_v1.2.json
```

To promote a new version: update the relevant path here and open a PR. CI will automatically run the eval against the new version and diff against the last saved run. Do not update `main.py` — it reads from `config.yaml`.

---

## CI/CD

The GitHub Actions workflow (`.github/workflows/eval.yml`) triggers on any PR that modifies files under `prompts/` or `data/golden_dataset_*.json`. It runs the full eval, posts a summary comment on the PR, and exits with code 1 on a critical regression — which blocks merge.

Required repository secrets: `DEEPSEEK_API_KEY`, `SLACK_WEBHOOK_URL` (optional).

To run in Docker:

```bash
docker build -t model-regression .
docker run -e DEEPSEEK_API_KEY=sk-... model-regression
```

---

## Architecture decisions

**Versioned YAML prompts instead of hardcoded strings.** Prompts are the artifact under test. Storing them as versioned files gives you a git history of every change, lets the eval pipeline record exactly which prompt version produced a given result, and lets non-engineers edit prompts without touching Python.

**Human-labeled golden dataset.** LLM-generated labels introduce circular validation — the model being tested and the model that wrote the labels share the same blind spots. Failures become invisible. All labels in this dataset were set by hand.

**LLM-as-judge for summary scoring.** Summaries cannot be evaluated with string matching; two valid summaries of the same email will be worded differently. A separate judge call scores semantic relevance on a 1–5 scale. The judge uses the same model as the classifier — cheaper and fast enough for this scale. At higher scale, use a stronger model as judge.

**Per-run diff plus rolling drift detection.** Per-run diffs catch sudden regressions from a single prompt change. Drift detection catches gradual degradation where no single run exceeds the threshold but accuracy has been slowly declining. Both are needed; neither alone is sufficient.

**Drift filtered by dataset version.** Drift is only computed across runs that share the same dataset version. Comparing runs across dataset versions is apples to oranges — earlier datasets had fewer or differently-labeled cases, and the accuracy difference reflects the eval bar changing, not model degradation.
