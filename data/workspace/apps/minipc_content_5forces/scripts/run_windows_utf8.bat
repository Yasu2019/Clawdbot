@echo off
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo === MiniPC Content 5-Forces Gate ===
echo UTF-8 mode enabled.

if not exist .venv (
    echo Creating .venv ...
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat

python -m pip install --upgrade pip
pip install -r backend\requirements.txt

echo.
echo Running sample CSV evaluation...
python cli\evaluate_idea.py --csv data\sample_ideas_utf8.csv --output data\sample_ideas_scored_excel_safe.csv

echo.
echo Starting API server at http://localhost:8765
echo Stop with Ctrl+C
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8765
