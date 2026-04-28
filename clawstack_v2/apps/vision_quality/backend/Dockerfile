FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY prompts ./prompts

EXPOSE 18796

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "18796"]
