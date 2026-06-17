import re, shutil
from pathlib import Path
from gradio_client import Client, handle_file
tok=None
for l in Path('D:/Clawdbot_Docker_20260125/.env').read_text(errors='ignore').splitlines():
    m=re.match(r'\s*HF_TOKEN\s*=\s*["\']?([^"\']+)',l)
    if m: tok=m.group(1).strip()
c = Client('theYiran/PartCrafter', token=tok, verbose=False)
try: c.predict(api_name='/start_session')
except: pass
print('submit EXACT defaults...', flush=True)
res = c.predict(handle_file('D:/Temp/mecha_src.png'), 4, 0, 1024, 50, 7.0, False, True,
                api_name='/run_partcrafter')
print('RESULT:', res); shutil.copy(res,'D:/Temp/mecha_parts.glb'); print('SAVED')
