from pydantic import BaseModel, field_validator
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
