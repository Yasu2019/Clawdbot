# -*- coding: utf-8 -*-
"""Regenerate a robust Kaggle PartCrafter notebook (all known fixes baked in).
Uses list-of-lines cell sources (canonical nbformat) to avoid escaping bugs."""
import base64, json
from pathlib import Path

b64 = base64.b64encode(Path('D:/Temp/mecha_768.jpg').read_bytes()).decode()

def code(src):  # src: triple-quoted string -> list of lines (canonical nbformat)
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": src.splitlines(keepends=True)}
def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.splitlines(keepends=True)}

c0 = md("""# PartCrafter on Kaggle — image -> parts GLB (robust build)

**REQUIRED (notebook can't set these for you):**
- Right panel **Settings -> Accelerator = GPU T4 x2**
- Right panel **Settings -> Internet = On**  (needed for git clone + pip + model download)

Then **Run All**. The input image is embedded (no upload). At the end a `.glb` appears
in the **Output** panel. Cell 2 takes ~15 min (mostly silent except [1/5]..[5/5] markers).""")

c1 = code("""# 1) GPU check (must show Tesla T4). If this errors -> GPU not enabled in Settings.
!nvidia-smi
""")

c2 = code('''# 2) Install PartCrafter (~15 min). Progress is printed between steps.
import os, time, subprocess, sys
t0 = time.time()
os.chdir('/kaggle/working')
if not os.path.isdir('PartCrafter/.git'):
    rc = os.system('git clone https://github.com/wgsxm/PartCrafter.git')
    assert rc == 0, 'git clone FAILED -> turn Internet ON in Settings, then re-run.'
os.chdir('/kaggle/working/PartCrafter')
print('[1/5] pin torch 2.5.1+cu124 ...', flush=True)
!pip install -q torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu124
print('[2/5] setup.sh (repo requirements; numpy downgrade warnings are harmless) ...', flush=True)
!bash settings/setup.sh
print('[3/5] transformers<5 + diffusers 0.38 (hub/tokenizers auto-resolved) ...', flush=True)
!pip install -q "transformers<5" "diffusers==0.38.0"
print('[4/5] build torch_cluster FROM SOURCE (3-8 min, please wait) ...', flush=True)
os.environ['CUDA_HOME'] = '/usr/local/cuda'
os.environ['FORCE_CUDA'] = '1'
os.environ['TORCH_CUDA_ARCH_LIST'] = '7.5'
!pip uninstall -y -q torch-cluster
!pip install -q --no-cache-dir --no-build-isolation torch-cluster
print('[5/5] install finished in %d sec' % int(time.time() - t0), flush=True)
''')

c2b = code('''# 2b) Import check (full pipeline incl. torch_cluster). MUST print IMPORTS OK.
import subprocess, sys
r = subprocess.run([sys.executable, '-c',
    'import torch, transformers, diffusers; from torch_cluster import fps; '
    'from src.pipelines.pipeline_partcrafter import PartCrafterPipeline; '
    'print("IMPORTS OK | torch", torch.__version__, "| transformers", transformers.__version__, '
    '"| diffusers", diffusers.__version__, "| cuda", torch.cuda.is_available())'],
    cwd='/kaggle/working/PartCrafter',
    env={**os.environ, 'PYTHONPATH': '/kaggle/working/PartCrafter'},
    capture_output=True, text=True)
print(r.stdout)
print(r.stderr[-2000:] if r.returncode else '')
print('RESULT:', 'OK' if r.returncode == 0 else 'FAILED (paste the lines above)')
''')

c3 = code('''# 3) Decode the EMBEDDED input image (no upload needed)
import base64
IMG = '/kaggle/working/PartCrafter/mecha_src.jpg'
open(IMG, 'wb').write(base64.b64decode(B64))
print('wrote', IMG)
''')
# prepend the base64 literal as the first source line of the decode cell
c3["source"] = ['B64 = "' + b64 + '"\n'] + c3["source"]

c4 = code('''# 4) Generate parts. CAPTURES + SHOWS the inference output so errors are visible.
# num_parts=4 + num_tokens=768 keeps it within T4 memory. Raise num_parts later if it works.
NUM_PARTS = 4
import os, subprocess, sys
os.chdir('/kaggle/working/PartCrafter')
env = dict(os.environ, PYTHONPATH='/kaggle/working/PartCrafter')
cmd = [sys.executable, 'scripts/inference_partcrafter.py',
       '--image_path', '/kaggle/working/PartCrafter/mecha_src.jpg',
       '--num_parts', str(NUM_PARTS), '--tag', 'mecha', '--render',
       '--num_tokens', '768']
p = subprocess.run(cmd, env=env, capture_output=True, text=True)
print('===== STDOUT (last 4000) =====')
print(p.stdout[-4000:])
print('===== STDERR (last 4000) =====')
print(p.stderr[-4000:])
print('inference exit code:', p.returncode)
''')

c5 = code('''# 5) Collect the GLB into /kaggle/working (download from the right Output panel)
import glob, os, shutil
glbs = sorted(glob.glob('/kaggle/working/PartCrafter/results/**/*.glb', recursive=True),
              key=os.path.getmtime)
print('GLB files:', glbs)
if glbs:
    out = '/kaggle/working/mecha_parts.glb'
    shutil.copy(glbs[-1], out)
    print('SAVED', out, os.path.getsize(out), 'bytes -> download from the Output panel')
    from IPython.display import FileLink
    display(FileLink('mecha_parts.glb'))
else:
    print('No GLB - check cell 4 output (OOM -> set NUM_PARTS=4 and re-run cell 4).')
''')

nb = {"cells": [c0, c1, c2, c2b, c3, c4, c5],
      "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                   "accelerator": "GPU", "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 5}

out = Path('D:/Clawdbot_Docker_20260125/data/workspace/partcrafter/PartCrafter_Kaggle.ipynb')
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')

# ---- validate ----
import ast
nb2 = json.load(open(out, encoding='utf-8'))
print('wrote', out, out.stat().st_size, 'bytes |', len(nb2['cells']), 'cells')
bad = 0
for i, c in enumerate(nb2['cells']):
    if c['cell_type'] != 'code':
        continue
    src = ''.join(c['source'])
    # strip jupyter ! / % magic lines for a pure-python syntax check
    lines = [l for l in src.splitlines() if not l.lstrip().startswith(('!', '%'))]
    try:
        ast.parse('\n'.join(lines))
    except SyntaxError as e:
        bad += 1
        print('  cell', i, 'SYNTAX ERROR:', e)
print('VALID json. code cells with python syntax errors:', bad)
