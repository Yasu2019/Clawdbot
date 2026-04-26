from datetime import datetime
from pathlib import Path
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('message')
ap.add_argument('--act', default='ACT.md')
args = ap.parse_args()
act = Path(args.act)
text = act.read_text(encoding='utf-8') if act.exists() else '# ACT.md\n\n## 作業ログ\n'
line = f"\n- {datetime.now().strftime('%Y-%m-%d %H:%M')}: {args.message}\n"
if '## 作業ログ' in text:
    text = text.replace('## 作業ログ\n', '## 作業ログ\n' + line, 1)
else:
    text += '\n## 作業ログ\n' + line
act.write_text(text, encoding='utf-8')
print(f'Updated {act}')
