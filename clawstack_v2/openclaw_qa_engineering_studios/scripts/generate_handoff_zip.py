from pathlib import Path
import zipfile
from datetime import datetime

root = Path(__file__).resolve().parents[1]
out = root.parent / f'openclaw_qa_engineering_studios_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for p in root.rglob('*'):
        if p.is_file():
            z.write(p, p.relative_to(root.parent))
print(out)
