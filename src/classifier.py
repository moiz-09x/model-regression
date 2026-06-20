import json
import os
import time
import yaml
from pathlib import Path
from openai import OpenAI
from pydantic import ValidationError

from src.models import PromptConfig, ClassifierOutput, ClassifierResult


def load_prompt(path: str | Path) -> PromptConfig:
    with open(path) as f:
        data = yaml.safe_load(f)
    return PromptConfig(**data)


def classify_email(
    email: str,
    prompt: PromptConfig,
    model: str = "deepseek-v4-flash",
    max_retries: int = 2,
) -> ClassifierResult:
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )
    user_message = prompt.user_prompt_template.format(email=email)

    last_error = None
    for attempt in range(max_retries + 1):
        messages = [{"role": "system", "content": prompt.system_prompt}]

        if attempt > 0:
            # Self-correction pass: tell the LLM what went wrong
            messages.append({"role": "user", "content": user_message})
            messages.append({"role": "assistant", "content": last_raw_output})
            messages.append({
                "role": "user",
                "content": (
                    f"Your previous response was invalid. Error: {last_error}\n"
                    f"Return ONLY a valid JSON object with keys 'category' and 'summary'. "
                    f"category must be one of: billing, technical, account, general."
                ),
            })
        else:
            messages.append({"role": "user", "content": user_message})

        start = time.perf_counter()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        last_raw_output = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(last_raw_output)
            output = ClassifierOutput(**parsed)
            return ClassifierResult(
                email=email,
                output=output,
                prompt_version=prompt.version,
                model=model,
                latency_ms=round(latency_ms, 2),
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )
        except (json.JSONDecodeError, ValidationError, KeyError) as e:
            last_error = str(e)

    raise RuntimeError(
        f"Classifier failed after {max_retries + 1} attempts. Last error: {last_error}\n"
        f"Last output: {last_raw_output}"
    )
