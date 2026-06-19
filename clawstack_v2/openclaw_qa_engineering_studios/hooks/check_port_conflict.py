import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import re
import sys
from pathlib import Path

PORT_RE = re.compile(r'\b(?:(?:127\.0\.0\.1|0\.0\.0\.0):)?(\d{2,5}):(\d{2,5})\b')

def scan(root: Path):
    ports = {}
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
                elif p.is_file() and p.name.lower().endswith('.yml') and 'compose' in p.name.lower():
                    # Parse ports within this compose file
                    file_ports = {}
                    text = p.read_text(encoding='utf-8', errors='ignore')
                    for i, line in enumerate(text.splitlines(), 1):
                        clean_line = line.strip()
                        if clean_line.startswith('#'):
                            continue
                        m = PORT_RE.search(clean_line)
                        if m:
                            port = m.group(1)
                            file_ports.setdefault(port, []).append((p, i, clean_line))
                    for port, refs in file_ports.items():
                        if len(refs) > 1:
                            ports.setdefault(p, []).append((port, refs))
        except Exception:
            continue
    return ports

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    dup = scan(root)
    if dup:
        print('[NG] Possible host port conflicts within compose files:')
        for p, conflicts in dup.items():
            print(f'FILE: {p}')
            for port, refs in conflicts:
                print(f'  PORT {port}')
                for file_path, i, line in refs:
                    print(f'    Line {i}: {line}')
        sys.exit(1)
    print('[OK] No duplicate host ports found in compose files.')