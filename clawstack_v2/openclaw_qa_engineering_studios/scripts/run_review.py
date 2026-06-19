import argparse
import subprocess
import sys
from pathlib import Path

HOOKS = {
    'sql_readonly': 'check_sql_readonly.py',
    'secret_leak': 'check_secret_leak.py',
    'port_conflict': 'check_port_conflict.py',
    'portal_duplicate': 'check_portal_duplicate.py',
    'iatf_evidence': 'check_iatf_evidence.py',
    'vba_destructive': 'check_vba_destructive.py',
    'act_updated': 'check_act_updated.py',
    'dashboard_freshness': 'check_dashboard_freshness.py',
}
MODES = {
    'solo': ['sql_readonly','secret_leak','act_updated'],
    'lean': ['sql_readonly','secret_leak','port_conflict','portal_duplicate','iatf_evidence','act_updated','dashboard_freshness'],
    'full': ['sql_readonly','secret_leak','port_conflict','portal_duplicate','iatf_evidence','vba_destructive','act_updated','dashboard_freshness'],
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=MODES, default='lean')
    ap.add_argument('--root', default='.')
    args = ap.parse_args()
    base = Path(__file__).resolve().parents[1]
    root = Path(args.root).resolve()
    failed = 0
    print(f'OpenClaw QA Engineering Studios review mode={args.mode} root={root}')
    for key in MODES[args.mode]:
        hook = base / 'hooks' / HOOKS[key]
        print(f'\n=== {key} ===')
        rc = subprocess.call([sys.executable, str(hook), str(root)])
        if rc == 1:
            failed += 1
        elif rc == 2:
            print('[WARN only] Continuing.')
    if failed:
        print(f'\n[RESULT] NG: {failed} blocking issue(s).')
        return 1
    print('\n[RESULT] OK: no blocking issues.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
