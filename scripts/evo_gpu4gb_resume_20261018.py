"""Resume one checkpoint-verified case after the authorized GPU reservation change."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from datetime import datetime
p=argparse.ArgumentParser();p.add_argument('--case',choices=['P1r43f','P1r44f'],required=True)
p.add_argument('--attempt',choices=['initial','after-reboot-2238'],default='initial');a=p.parse_args()
root=Path('/srv/evo-hpc/gpu4gb-maintenance-20261018')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
state=json.loads((root/'state.json').read_text())
assert state['phase']=='verified-stopped-ready-for-gpu-change'
m=json.loads((root/a.case/'manifest.json').read_text());d=Path(m['directory'])
binary=Path(m['resume_argv'][0]);assert sha(binary)==m['binary_sha256']
for name,proof in m['files'].items():
    assert sha(d/name)==proof['sha256'],('Changed live checkpoint/input',name)
    assert sha(root/a.case/name)==proof['sha256'],('Changed immutable recovery copy',name)
for proc in Path('/proc').glob('[0-9]*'):
    try:
        if (proc/'cwd').resolve()==d and (proc/'cmdline').read_bytes().startswith(str(binary).encode()+b'\0'):
            raise RuntimeError('Existing live engine; never launch a duplicate')
    except (OSError,FileNotFoundError):pass
suffix='' if a.attempt=='initial' else '.'+a.attempt
lock=root/(a.case+suffix+'.resume-owner.json')
with lock.open('x') as f:json.dump({'owner_pid':os.getpid(),'created_at':datetime.now().astimezone().isoformat()},f)
env=os.environ.copy();b='/opt/openradioss/OpenRadioss'
env.update(ORS_ROOT=b,RAD_CFG_PATH=b+'/hm_cfg_files',LD_LIBRARY_PATH=b+'/exec:'+b+'/extlib/hm_reader/linux64',OMP_NUM_THREADS=str(m['threads']),OPENBLAS_NUM_THREADS='1')
status=root/(a.case+suffix+'.resume-status.json')
with (d/('engine_gpu4gb_resume'+suffix+'.log')).open('x') as log:
    engine=subprocess.Popen(m['resume_argv'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT)
    status.write_text(json.dumps({'observed_at':datetime.now().astimezone().isoformat(),'state':'running','pid':engine.pid,'case_id':a.case,'resume_time':m['simulation_time'],'threads':m['threads'],'mpi_domains':m['mpi_domains']}))
    code=engine.wait()
status.write_text(json.dumps({'observed_at':datetime.now().astimezone().isoformat(),'state':'exited-needs-endpoint-review','exit_code':code,'case_id':a.case}))
raise SystemExit(code)
