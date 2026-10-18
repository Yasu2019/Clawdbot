"""AMD ADLX 1.5 VGM enumeration; read-only unless explicit authorized apply flag.
ABI source: AMD GPUOpen ADLX SDK Include/{ADLX,ISystem,ISystem3,ICollections}.h.
"""
import ctypes as c
import json,sys,subprocess,hashlib
from datetime import datetime
from pathlib import Path

P=c.c_void_p
I=c.c_int
refs=[]
def call(obj,slot,result,*types):
    table=c.cast(obj,c.POINTER(c.POINTER(P))).contents
    return c.WINFUNCTYPE(result,P,*types)(table[slot])
def ok(code,label):
    if code != 0: raise RuntimeError(label+' ADLX_RESULT='+str(code))
def ptr(obj,slot):
    out=P();ok(call(obj,slot,I,c.POINTER(P))(obj,c.byref(out)),'Get interface')
    if not out.value: raise RuntimeError('Null interface')
    refs.append(out);return out
def option(o):
    name=c.c_char_p();mode=I();carved=c.c_double();remaining=c.c_double()
    ok(call(o,3,I,c.POINTER(c.c_char_p))(o,c.byref(name)),'Name')
    ok(call(o,4,I,c.POINTER(I))(o,c.byref(mode)),'Mode')
    ok(call(o,5,I,c.POINTER(c.c_double))(o,c.byref(carved)),'MemoryCarved')
    ok(call(o,6,I,c.POINTER(c.c_double))(o,c.byref(remaining)),'MemoryRemaining')
    return {'name':name.value.decode('utf-8'),'mode':mode.value,'memory_carved_GB':carved.value,'memory_remaining_GB':remaining.value}

report={'observed_at':datetime.now().astimezone().isoformat(),'read_only':True,'setter_called':False}
apply=sys.argv[1:]==['--apply-4gb-authorized']
if sys.argv[1:] and not apply:raise SystemExit('Unknown mode; no change')
initialized=False
try:
    dll=c.CDLL(r'C:\Windows\System32\amdadlx64.dll')
    dll.ADLXQueryFullVersion.argtypes=[c.POINTER(c.c_uint64)];dll.ADLXQueryFullVersion.restype=I
    version=c.c_uint64();ok(dll.ADLXQueryFullVersion(c.byref(version)),'Version')
    report['runtime_full_version']=version.value
    dll.ADLXInitialize.argtypes=[c.c_uint64,c.POINTER(P)];dll.ADLXInitialize.restype=I
    system=P();ok(dll.ADLXInitialize(version,c.byref(system)),'Initialize');initialized=True
    system3=P();ok(call(system,2,I,c.c_wchar_p,c.POINTER(P))(system,'IADLXSystem3',c.byref(system3)),'IADLXSystem3')
    refs.append(system3)
    vgm=ptr(system3,6)
    supported=c.c_uint32();ok(call(vgm,3,I,c.POINTER(c.c_uint32))(vgm,c.byref(supported)),'IsSupported')
    report['supported']=bool(supported.value)
    if not supported.value: raise RuntimeError('VGM unsupported on this host/driver/session')
    report['current']=option(ptr(vgm,5))
    options=ptr(vgm,6)
    begin=call(options,5,c.c_uint)(options);end=call(options,6,c.c_uint)(options)
    if end-begin>32: raise RuntimeError('Unexpected option count')
    report['options']=[];target=None
    for idx in range(begin,end):
        o=P();ok(call(options,11,I,c.c_uint,c.POINTER(P))(options,idx,c.byref(o)),'At_OptionList')
        refs.append(o);entry=option(o);report['options'].append(entry)
        if entry['memory_carved_GB']==4.0:target=o
    if apply:
        if target is None:raise RuntimeError('Exact4GB option unavailable; no substitution')
        checkpoint=Path(r'C:\ProgramData\Clawstack\EvoGpu4GB-20261018\checkpoint-state.json')
        proof=json.loads(checkpoint.read_text(encoding='utf-8'))
        assert proof['phase']=='verified-stopped-ready-for-gpu-change' and len(proof['cases'])==2
        assert (datetime.now().astimezone()-datetime.fromisoformat(proof['verified_at'])).total_seconds()<1800
        # Last live check immediately before an API that may reboot the host.
        code="from pathlib import Path; import sys; rows=[]\nfor p in Path('/proc').glob('[0-9]*'):\n try:\n  cmd=(p/'cmdline').read_bytes().split(b'\\0')[0]\n  if b'engine_linux64_gf' in cmd: rows.append(p.name)\n except OSError: pass\nprint('active_engines='+str(len(rows)));sys.exit(bool(rows))"
        checked=subprocess.run(['wsl','-d','EVO-OpenFOAM-20261018','-u','root','--','python3','-c',code],capture_output=True,timeout=30)
        assert checked.returncode==0,'Engine still present or live probe failed; no change'
        report.update(read_only=False,setter_called=True,target_GB=4.0,checkpoint_state_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),authorization='User: GPU is unused; reduce to4GB')
        intent=checkpoint.parent/'gpu4gb-set-intent.json'
        intent.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('Verified native checkpoints; calling authorized ADLX SetOption4GB, which may restart Windows.',flush=True)
        report['set_result']=call(vgm,7,I,P)(vgm,target)
except Exception as exc:
    report['error']=str(exc)
finally:
    for o in reversed(refs): call(o,1,c.c_long)(o)
    if initialized:
        dll.ADLXTerminate.argtypes=[];dll.ADLXTerminate.restype=I
        report['terminate_result']=dll.ADLXTerminate()
    text=json.dumps(report,ensure_ascii=False,indent=2)
    Path(__file__).with_suffix('.report.json').write_text(text,encoding='utf-8')
    print(text)
