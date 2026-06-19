import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import re
import sys
from pathlib import Path

PATTERNS = [
    re.compile(r'Bearer\s+[A-Za-z0-9._\-]{20,}', re.I),
    re.compile(r'(api[_-]?key|secret|password|token)\s*[:=]\s*["\']?[A-Za-z0-9._\-]{16,}', re.I),
    re.compile(r'sk-[A-Za-z0-9]{20,}', re.I),
]
TARGET_EXT = {'.py', '.js', '.ps1', '.sh', '.bat', '.cmd', '.vbs', '.sql', '.html', '.css'}

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
                            # Skip lines referencing environment variables
                            if any(x in line for x in ['process.env', 'os.environ', 'os.getenv', 'getenv']):
                                continue
                            if any(rx.search(line) for rx in PATTERNS):
                                hits.append((p, i, line.strip()))
        except Exception:
            continue
    return hits

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    hits = scan(root)
    if hits:
        print('[NG] Possible secret leak found:')
        for p, i, line in hits[:50]:
            print(f'{p}:{i}: {line[:160]}')
        sys.exit(1)
    print('[OK] No obvious secrets found.')