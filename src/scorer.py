from __future__ import annotations

import os
from openai import OpenAI


_JUDGE_PROMPT = """You are an evaluation judge for a customer support classifier.

You will be given:
- The original customer email
- An expected summary (human-written reference)
- An actual summary (produced by the classifier)

Score the actual summary from 1 to 5 using this scale:
  5 - Captures the core issue accurately and concisely. Meaning matches the expected summary.
  4 - Mostly correct. Minor wording differences but no information lost.
  3 - Partially correct. Gets the general topic right but misses an important detail.
  2 - Weak. Vague or only tangentially related to the actual issue.
  1 - Wrong. Describes a different issue or hallucinates content not in the email.

Return only a single integer between 1 and 5. No explanation, no punctuation, nothing else."""


def score_summary(
    email: str,
    expected_summary: str,
    actual_summary: str,
    model: str = "deepseek-v4-flash",
) -> int:
    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )

    user_message = (
        f"Customer email:\n{email}\n\n"
        f"Expected summary:\n{expected_summary}\n\n"
        f"Actual summary:\n{actual_summary}"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _JUDGE_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content.strip()

    try:
        score = int(raw)
        if score < 1 or score > 5:
            raise ValueError
        return score
    except ValueError:
        # Judge returned something unexpected — default to middle score and don't crash the run
        return 3
