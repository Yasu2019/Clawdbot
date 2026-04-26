import json, yaml
from pathlib import Path
cfg = yaml.safe_load(Path('/mnt/d/Clawdbot_Docker_20260125/data/workspace/clawstack_unified_compose_config.yaml').read_text())
services = cfg.get('services', {})
out = {}
for name, s in services.items():
    dep = s.get('depends_on') or {}
    deps = list(dep.keys()) if isinstance(dep, dict) else dep
    out[name] = {
        'ports': s.get('ports', []),
        'depends_on': deps,
        'build': bool(s.get('build')),
        'image': s.get('image'),
        'volume_count': len(s.get('volumes', []) or []),
    }
print(json.dumps(out, ensure_ascii=False, indent=2))
