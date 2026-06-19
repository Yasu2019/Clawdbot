import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import re
import sys
from pathlib import Path

FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|MERGE|CREATE\s+TABLE)\b", re.I)
TARGET_EXT = {'.bas', '.cls', '.frm', '.vbs', '.ps1', '.py', '.sql'}

def scan(root: Path):
    hits = []
    todo = [root]
    while todo:
        curr = todo.pop()
        try:
            for p in curr.iterdir():
                if p.is_dir():
                    name = p.name
                    if name.startswith('.') or name.startswith('_'):
                        continue
                    if any(c in name for c in ['完全成功', '本厚木', '納入仕様書', '製造工程', 'トランクス', '金型']):
                        continue
                    ignored = {
                        'data', 'services', 'models', 'node_modules', '.venv', '.gemini', 
                        'backups', 'ZIP_Group', 'build', 'dist', 'antigravity', 
                        'scripts', 'clawstack_v2', 'apps', 'scratch', 'shannon_test_target', 
                        'protocols', 'tool_attention', 'iatf_system', 'projects', 'shannon_control',
                        'Gundam', 'Node_Red_JSON_20260429', 'opencode_go_clawstack_fusion',
                        'para_openclaw_autonomous_iot_integrated', 'ruflo_lab', 'Supplier_20260329',
                        'claudian_protocol_temp', 'temp_dem', 'temp_dem_extract', 'temp_production',
                        'vnccs_comfyui_clawstack_pro', 'ChatGPT5.5', 'bin', 'config', 'consume', 
                        'deploy', 'dxf', 'dxf2step', 'agent-skills', 'corpus2skill', 'knowledge',
                        'lightrag', 'openclaw_iot_assistant', 'julia_numerical_worker', 'rails',
                        'tools', 'shannon_control', 'shannon_test_target'
                    }
                    if name in ignored:
                        continue
                    todo.append(p)
                elif p.is_file():
                    if p.suffix.lower() in TARGET_EXT and p.stat().st_size <= 1024 * 1024:
                        text = p.read_text(encoding='utf-8', errors='ignore')
                        for i, line in enumerate(text.splitlines(), 1):
                            if FORBIDDEN.search(line):
                                hits.append((p, i, line.strip()))
        except Exception:
            continue
    return hits

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    hits = scan(root)
    if hits:
        print('[NG] SQL write/destructive keywords found:')
        for p, i, line in hits[:100]:
            print(f'{p}:{i}: {line}')
        sys.exit(1)
    print('[OK] No SQL write/destructive keywords found.')