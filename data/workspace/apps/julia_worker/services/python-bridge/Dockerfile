FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app

ENV PYTHONUNBUFFERED=1
ENV PYTHON_BRIDGE_PORT=8097
ENV JULIA_WORKER_URL=http://julia-numerical-worker:8096

EXPOSE 8097

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8097"]
