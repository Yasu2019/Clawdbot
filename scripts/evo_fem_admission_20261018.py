"""Read-only live admission report; never starts, kills or steals a job/lock."""
import argparse,json,os,re,subprocess,time
from pathlib import Path
from datetime import datetime

GIB=1024**3
def decide(policy, jobs, guest_available, host_available, requested_threads, requested_peak):
    reasons=[]
    threads=sum(j['threads'] for j in jobs)
    peaks=sum(j['reserved_peak_gib'] for j in jobs)
    unbudgeted=[j['pid'] for j in jobs if not j['budget_identified']]
    if unbudgeted:reasons.append('Active solver without an identified peak-memory budget')
    if any(j['rss_gib']>j['reserved_peak_gib'] for j in jobs):reasons.append('Active solver exceeded its planned memory reservation; reassess before adding work')
    thread_free=max(0,policy['solver_thread_cap']-threads)
    memory_free=max(0,policy['guest_configured_gib']-policy['guest_reserve_gib']-peaks)
    memory_free=min(memory_free,max(0,guest_available-policy['guest_reserve_gib']))
    if host_available is None:
        reasons.append('Live Windows available memory unavailable')
        memory_free=0
    else:memory_free=min(memory_free,max(0,host_available-policy['windows_reserve_gib']))
    if requested_threads>thread_free:reasons.append('Requested threads exceed remaining aggregate solver budget')
    if requested_peak>memory_free:reasons.append('Requested peak memory exceeds live host/guest budget')
    return {'resource_budget_fits':not reasons,'reasons':reasons,'active_solver_threads':threads,
            'active_reserved_peak_gib':peaks,'remaining_solver_threads':thread_free,
            'additional_peak_gib_ceiling':round(memory_free,2)}

def collect_jobs(policy):
    jobs=[]
    for p in Path('/proc').glob('[0-9]*'):
        try:
            argv=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
            if not argv:continue
            name=Path(argv[0]).name
            if not (name.startswith('engine_linux') or name in ['ccx','ccx_preCICE','ElmerSolver','foamRun'] or name.endswith('Foam')):continue
            cwd=str((p/'cwd').resolve());status=(p/'status').read_text()
            rss=int(re.search(r'VmRSS:\s+(\d+)',status)[1])*1024/GIB
            actual=int(re.search(r'Threads:\s+(\d+)',status)[1])
            threads=int(argv[argv.index('-nt')+1]) if '-nt' in argv else actual
            budget=policy['case_budgets'].get(cwd)
            # Unknown live work is observed, not overwritten, killed or assumed idle.
            peak=float(budget['peak_gib']) if budget else rss
            jobs.append({'pid':int(p.name),'solver':name,'directory':cwd,'threads':threads,
                'rss_gib':round(rss,3),'reserved_peak_gib':peak,'budget_identified':budget is not None})
        except (OSError,ValueError,AttributeError):continue
    return jobs

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--policy',default='/opt/evo-hpc/fem-policy-20261018.json')
    p.add_argument('--request-threads',type=int,default=0)
    p.add_argument('--request-peak-gib',type=float,default=0)
    args=p.parse_args()
    if args.request_threads<0 or args.request_peak_gib<0:raise SystemExit('Negative resource request')
    policy=json.loads(Path(args.policy).read_text())
    raw=Path('/proc/meminfo').read_text();guest=int(re.search(r'MemAvailable:\s+(\d+)',raw)[1])*1024/GIB
    host=None;host_observed=None;host_disk=None
    try:
        code="$o=Get-CimInstance Win32_OperatingSystem;$d=Get-Volume -DriveLetter C;[pscustomobject]@{observed_at=(Get-Date -Format o);available_bytes=[double]$o.FreePhysicalMemory*1024;physical_disk_free_bytes=$d.SizeRemaining}|ConvertTo-Json -Compress"
        r=subprocess.run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe','-NoProfile','-NonInteractive','-Command',code],capture_output=True,text=True,timeout=15)
        if r.returncode==0:
            h=json.loads(r.stdout);host=float(h['available_bytes'])/GIB;host_observed=h['observed_at'];host_disk=float(h['physical_disk_free_bytes'])/GIB
    except (OSError,ValueError,subprocess.TimeoutExpired):pass
    jobs=collect_jobs(policy)
    result=decide(policy,jobs,guest,host,args.request_threads,args.request_peak_gib)
    if host_disk is None or host_disk<policy.get('physical_disk_reserve_gib',50):
        result['resource_budget_fits']=False;result['reasons'].append('Backing physical disk unavailable or below free-space reserve')
    result.update(observed_at=datetime.now().astimezone().isoformat(),source='Live procfs and Windows CIM; planned case reservations from explicit policy',
        host_memory_observed_at=host_observed,windows_available_gib=None if host is None else round(host,2),guest_available_gib=round(guest,2),
        jobs=jobs,guest_online_cpus=os.cpu_count(),requested_threads=args.request_threads,requested_peak_gib=args.request_peak_gib,
        physical_backing_disk_free_gib=None if host_disk is None else round(host_disk,2),
        dispatch_authorized=False,checkpoint_gate='Before any production dispatch, separately verify case-native checkpoints, inputs, binary, MPI/thread layout and exact resume procedure. This resource check alone never authorizes dispatch.',
        guard_type='admission_preflight_only',temperature_core_average_c=None,temperature_note='No verified complete core-average telemetry; no fabricated average or maximum-to-average substitution.',
        legacy_locks='Preserved; this checker does not acquire, clear or reuse legacy claims')
    print(json.dumps(result,indent=2))
    return 0 if result['resource_budget_fits'] else 2
if __name__=='__main__':raise SystemExit(main())
