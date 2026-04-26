from pathlib import Path
import zipfile
base=Path(__file__).resolve().parents[1]
out=base.with_suffix('.zip')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for p in base.rglob('*'):
        if p.is_file() and p.name != out.name:
            z.write(p, p.relative_to(base.parent))
print(out)
