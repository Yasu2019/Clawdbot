# Docker 実装例

## 1. 方針
MarkItDown をコンテナ化し、ホスト上の `raw_docs` を読み、`processed_md` に Markdown を出力する。

## 2. シンプルな Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir markitdown

COPY runner.py /app/runner.py

CMD ["python", "/app/runner.py"]
```

## 3. runner.py 例
```python
from pathlib import Path
import subprocess
import csv
import time

in_dir = Path("/data/raw_docs")
out_dir = Path("/data/processed_md")
log_dir = Path("/data/logs")

out_dir.mkdir(parents=True, exist_ok=True)
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / f"markitdown_run_{int(time.time())}.csv"
targets = {".pdf", ".docx", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg", ".zip"}

with log_file.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["input_file", "status", "output_file", "message"])

    for p in in_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in targets:
            out_path = out_dir / (p.stem + ".md")
            try:
                result = subprocess.run(
                    ["markitdown", str(p)],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                out_path.write_text(result.stdout, encoding="utf-8-sig")
                writer.writerow([str(p), "SUCCESS", str(out_path), ""])
            except Exception as e:
                writer.writerow([str(p), "FAIL", "", str(e)])
```

## 4. docker-compose.yml 例
```yaml
services:
  markitdown-poc:
    build: .
    container_name: markitdown-poc
    volumes:
      - ./data:/data
    restart: "no"
```
