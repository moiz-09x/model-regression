FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runtime environment variables — provide these at docker run time
# DEEPSEEK_API_KEY, SLACK_WEBHOOK_URL

CMD ["python", "main.py"]
