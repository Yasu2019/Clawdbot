FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
COPY requirements-core.txt .
RUN pip install --no-cache-dir -r requirements-core.txt
COPY . .
ENV PYTHONPATH=/app/src
CMD ["python", "scripts/run_api.py", "--host", "0.0.0.0"]
