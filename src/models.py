from pydantic import BaseModel, field_validator, computed_field
from typing import Literal, Optional
from datetime import datetime


class PromptConfig(BaseModel):
    version: str
    created_at: str
    description: str
    system_prompt: str
    user_prompt_template: str


class ClassifierOutput(BaseModel):
    category: Literal["billing", "technical", "account", "general"]
    summary: str

    @field_validator("summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("summary cannot be empty")
        return v.strip()


class TestCase(BaseModel):
    id: str
    email: str
    expected_category: Literal["billing", "technical", "account", "general"]
    expected_summary: str
    difficulty: Literal["easy", "medium", "hard"]
    notes: str


class GoldenDataset(BaseModel):
    version: str
    created_at: str
    description: str
    test_cases: list[TestCase]


class ClassifierResult(BaseModel):
    email: str
    output: ClassifierOutput
    prompt_version: str
    model: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    timestamp: str = ""

    def model_post_init(self, __context):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


class CaseResult(BaseModel):
    test_case_id: str
    difficulty: Literal["easy", "medium", "hard"]
    expected_category: Literal["billing", "technical", "account", "general"]
    actual_category: Literal["billing", "technical", "account", "general"]
    category_match: bool
    expected_summary: str
    actual_summary: str
    summary_score: int                  # 1-5, from LLM judge
    latency_ms: float
    input_tokens: int
    output_tokens: int
    error: Optional[str] = None         # set if classifier raised instead of returning


class EvalRun(BaseModel):
    run_id: str
    prompt_version: str
    dataset_version: str
    model: str
    timestamp: str
    case_results: list[CaseResult]

    @computed_field
    @property
    def total_cases(self) -> int:
        return len(self.case_results)

    @computed_field
    @property
    def passed_cases(self) -> int:
        return sum(1 for r in self.case_results if r.category_match)

    @computed_field
    @property
    def accuracy(self) -> float:
        if not self.case_results:
            return 0.0
        return round(self.passed_cases / self.total_cases, 4)

    @computed_field
    @property
    def avg_summary_score(self) -> float:
        scores = [r.summary_score for r in self.case_results if not r.error]
        return round(sum(scores) / len(scores), 2) if scores else 0.0

    @computed_field
    @property
    def avg_latency_ms(self) -> float:
        latencies = [r.latency_ms for r in self.case_results if not r.error]
        return round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    @computed_field
    @property
    def total_tokens(self) -> int:
        return sum(r.input_tokens + r.output_tokens for r in self.case_results)

    def accuracy_for_category(self, category: str) -> float:
        cases = [r for r in self.case_results if r.expected_category == category]
        if not cases:
            return 0.0
        passed = sum(1 for r in cases if r.category_match)
        return round(passed / len(cases), 4)


class EvalDiff(BaseModel):
    baseline_run_id: str
    current_run_id: str
    accuracy_delta: float               # current - baseline, positive = improvement
    summary_score_delta: float
    status: Literal["pass", "warning", "critical"]
    regressions: list[str]             # test_case_ids that flipped pass → fail
    improvements: list[str]            # test_case_ids that flipped fail → pass
    per_category_delta: dict[str, float]  # category → accuracy delta
