import time
from pathlib import Path
from .qa import analyze_csv

WATCH = Path('/app/samples')
REPORTS = Path('/app/reports')
REPORTS.mkdir(exist_ok=True, parents=True)

def main():
    seen = set()
    while True:
        for p in WATCH.glob('*.csv'):
            if str(p) in seen:
                continue
            try:
                result = analyze_csv(str(p), 10)
                (REPORTS / f'{p.stem}_analysis.json').write_text(str(result), encoding='utf-8')
                seen.add(str(p))
            except Exception as e:
                (REPORTS / 'worker_errors.log').open('a', encoding='utf-8').write(f'{p}: {e}\n')
        time.sleep(60)

if __name__ == '__main__':
    main()
