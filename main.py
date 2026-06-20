from dotenv import load_dotenv
load_dotenv()

from src.evaluator import run_eval
from src.comparator import compare, load_latest_runs, print_diff

run = run_eval(
    prompt_path="prompts/support_classifier_v1.1.yaml",
    dataset_path="data/golden_dataset_v1.2.json",
)

runs = load_latest_runs(n=2)
if len(runs) == 2:
    diff = compare(baseline=runs[0], current=runs[1])
    print_diff(diff)
else:
    print("\nFirst run — no baseline to compare against yet.")
    print("Run again after changing the prompt to see a diff.")
