from dotenv import load_dotenv
load_dotenv()

from src.classifier import load_prompt, classify_email

prompt = load_prompt("prompts/support_classifier_v1.0.yaml")

test_emails = [
    "I can't log into my account, it keeps saying invalid password.",
    "I was charged twice for my subscription this month, please refund.",
    "Your API integration keeps returning a 500 error on our end.",
    "Hi, just wanted to say your product is great!",
]

for email in test_emails:
    result = classify_email(email, prompt)
    print(f"Email  : {email[:60]}...")
    print(f"Category : {result.output.category}")
    print(f"Summary  : {result.output.summary}")
    print(f"Latency  : {result.latency_ms}ms | Tokens: {result.input_tokens}in / {result.output_tokens}out")
    print("-" * 70)
