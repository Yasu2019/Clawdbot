"""Native graceful stop and immutable recovery evidence for authorized GPU change.
No signals, force kill, prior-attempt cleanup, or scheduler modification.
"""
import hashlib,json,os,re,shutil,time,sys
from pathlib import Path
from datetime import datetime
BASE=Path('/srv/evo-hpc')
ROOT=BASE/'gpu4gb-maintenance-20261018'
BIN=Path('/opt/openradioss/OpenRadioss/exec/engine_linux64_gf')
CASES=[('P1r43f',BASE/'panel-P1r43f-20261018',12),('P1r44f',BASE/'panel-P1r44f-r4-20261018',6)]
def now():return datetime.now().astimezone().isoformat()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def running(d):
    rows=[]
    for p in Path('/proc').glob('[0-9]*'):
        try:
            if (p/'cwd').resolve()!=d:continue
            cmd=(p/'cmdline').read_bytes().split(b'\0')
            if cmd and cmd[0].decode()==str(BIN):rows.append((int(p.name),[x.decode() for x in cmd if x]))
        except (OSError,RuntimeError):pass
    return rows
def write(p,obj):
    tmp=p.with_suffix('.partial');tmp.write_text(json.dumps(obj,indent=2),encoding='utf-8');tmp.replace(p)

finish_only=sys.argv[1:]==['--finish-existing-proof']
if finish_only:
    state=json.loads((ROOT/'state.json').read_text())
    assert state['phase']=='waiting-native-stop'
    assert state['authorization']=='User: reduce EVO GPU reservation to4GB'
    assert all(not running(d) for _,d,_ in CASES),'Do not repeat requests or disturb current engines'
else:
    ROOT.mkdir() # Never reuse an uncertain old maintenance attempt.
    state={'created_at':now(),'authorization':'User: reduce EVO GPU reservation to4GB','phase':'preflight','cases':[]}
    write(ROOT/'state.json',state)
for tag,d,nt in ([] if finish_only else CASES):
    r='PANEL4MM_'+tag
    procs=running(d)
    assert len(procs)==1,(tag,'Unexpected current engine family',procs)
    expected=[str(BIN),'-i',r+'_0002.rad','-nt',str(nt)]
    assert procs[0][1]==expected,(tag,'Engine arguments changed')
    assert not (d/(r+'_0002.ctl')).exists(),(tag,'Existing control file; preserve')
    assert (d/(r+'_0000_0001.rst')).stat().st_size>1024**3
    assert (d/(r+'_0001_0001.rst')).stat().st_size>1024**3
    assert '/RFILE' in (d/(r+'_0002.rad')).read_text()
    state['cases'].append({'case_id':tag,'directory':str(d),'threads':nt,'mpi_domains':1,'pid':procs[0][0],
        'binary_sha256':sha(BIN),'inputs':{p.name:sha(p) for p in d.glob('*.rad')},
        'prior_known_good_preserved':[r+'_0000_0001.rst',r+'_0001_0001.rst']})
if not finish_only:
    state['phase']='requesting-native-checkpoints';write(ROOT/'state.json',state)
requested=datetime.fromisoformat(state['created_at']).timestamp()
for tag,d,nt in ([] if finish_only else CASES):
    ctl=d/('PANEL4MM_'+tag+'_0002.ctl')
    # Atomic no-overwrite publication of this exact new request.
    tmp=ROOT/(tag+'.ctl.request');tmp.write_text('/CHKPT\n/STOP\n',encoding='ascii')
    os.link(tmp,ctl)
state['phase']='waiting-native-stop';write(ROOT/'state.json',state)
for _ in range(120):
    if all(not running(d) for _,d,_ in CASES):break
    time.sleep(3)
else:raise RuntimeError('Native stop not complete; preserve everything and do not reboot')
for item,(tag,d,nt) in zip(state['cases'],CASES):
    r='PANEL4MM_'+tag
    rst=d/(r+'_0002_0001.rst')
    assert rst.stat().st_mtime>=requested-2 and rst.stat().st_size>1024**3,(tag,'Missing fresh restart')
    before=(rst.stat().st_size,rst.stat().st_mtime_ns);time.sleep(3)
    assert before==(rst.stat().st_size,rst.stat().st_mtime_ns)
    check=(d/'CHECK_DATA').read_text().strip()
    assert check=='/RERUN/'+r+'/2',(tag,'Unexpected native CHECK_DATA',check)
    out=(d/'engine_run2.log').read_text(errors='replace')
    assert 'USER BREAK' in out.upper() or 'USER BREAK' in (d/(r+'_0002.out')).read_text(errors='replace').upper(),(tag,'Native stop evidence missing')
    steps=re.findall(r'NC=\s*(\d+)\s+T=\s*([\d.Ee+\-]+)',out)
    assert steps,(tag,'No progress evidence')
    assert sha(BIN)==item['binary_sha256']
    assert all(sha(d/name)==digest for name,digest in item['inputs'].items())
    dest=ROOT/tag;dest.mkdir(exist_ok=finish_only)
    files={}
    for p in [rst,d/'CHECK_DATA',*d.glob('*.rad')]:
        target=dest/p.name
        if not target.exists():shutil.copy2(p,target)
        a,b=sha(p),sha(target);assert a==b,(tag,'Snapshot mismatch')
        files[p.name]={'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,'sha256':a}
    ctl=d/(r+'_0002.ctl')
    if ctl.exists():
        # Radioss replaces commands with its RUN CONTROL FILE acknowledgement.
        # Confirm exact inode from our no-overwrite hardlink, not constant contents.
        assert os.path.samefile(ctl,ROOT/(tag+'.ctl.request')),'Control file replaced by another writer; preserve'
        acknowledgement=ctl.read_text()
        assert 'RUN CONTROL FILE' in acknowledgement and 'RUN STOP AT CURRENT CYCLE' in acknowledgement
        item['native_control_acknowledgement_sha256']=sha(ctl)
        native_cycle=re.search(r'CYCLE\s*=\s*(\d+)',acknowledgement)
        native_time=re.search(r'\bTIME\s*=\s*([\d.Ee+\-]+)',acknowledgement)
        assert native_cycle and native_time
        ctl.rename(dest/ctl.name) # Only this invocation's exact request, after engine exit.
    item.update({'stopped_at':now(),'cycle':int(native_cycle[1]),'simulation_time':float(native_time[1]),'snapshot':str(dest),'files':files,
        'resume_argv':[str(BIN),'-i','CHECK_DATA','-nt',str(nt)]})
    write(dest/'manifest.json',item)
state['phase']='verified-stopped-ready-for-gpu-change';state['verified_at']=now();write(ROOT/'state.json',state)
mirror=Path('/mnt/c/ProgramData/Clawstack/EvoGpu4GB-20261018');mirror.mkdir(exist_ok=True)
write(mirror/'checkpoint-state.json',state)
print(json.dumps({'phase':state['phase'],'cases':[{k:x[k] for k in ['case_id','cycle','simulation_time','snapshot']} for x in state['cases']]}),flush=True)
