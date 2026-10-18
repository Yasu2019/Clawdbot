#!/bin/bash
# Bounded two-rank functional/restart validation, not a production analysis.
set -o pipefail
source /usr/lib/openfoam/openfoam2512/etc/bashrc
set -e
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export OMPI_ALLOW_RUN_AS_ROOT=1 OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
root=/srv/evo-hpc/fem-capacity-maintenance-20261018/openfoam-restart-validation
test ! -e "$root"
mkdir "$root"
tutorial=$(find "$FOAM_TUTORIALS" -type d -path '*/icoFoam/cavity/cavity' -print -quit)
test -n "$tutorial"
cp -a "$tutorial" "$root/case"
cd "$root/case"
for pair in 'endTime 0.02' 'deltaT 0.005' 'writeControl runTime' 'writeInterval 0.01' 'purgeWrite 0' 'writeFormat ascii' 'writePrecision 12' 'startFrom startTime' 'startTime 0'; do
    set -- $pair
    foamDictionary system/controlDict -entry "$1" -set "$2" >/dev/null
done
cat > system/decomposeParDict <<'DICT'
FoamFile { version 2.0; format ascii; class dictionary; object decomposeParDict; }
numberOfSubdomains 2;
method scotch;
DICT
cp system/controlDict "$root/controlDict.initial"
blockMesh > log.blockMesh 2>&1
checkMesh > log.checkMesh 2>&1
decomposePar > log.decomposePar 2>&1
mpirun --bind-to core -np 2 icoFoam -parallel > log.initial 2>&1
grep -q '^End' log.initial
mkdir "$root/known-good-0.02"
for rank in 0 1; do
    for time in 0.01 0.02; do
        for field in U p phi; do test -s "processor$rank/$time/$field"; done
    done
    cp -a "processor$rank/0.02" "$root/known-good-0.02/processor$rank"
done
python3 - "$root" <<'PY'
import hashlib,json,sys
from pathlib import Path
from datetime import datetime
r=Path(sys.argv[1]);case=r/'case'
proof={'observed_at':datetime.now().astimezone().isoformat(),'mpi_ranks':2,'checkpoint_time':0.02,'files':{}}
for rank in range(2):
    for p in (case/f'processor{rank}/0.02').rglob('*'):
        if p.is_file():proof['files'][str(p.relative_to(case))]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(r/'checkpoint-before-resume.json').write_text(json.dumps(proof,indent=2))
PY
foamDictionary system/controlDict -entry startFrom -set latestTime >/dev/null
foamDictionary system/controlDict -entry endTime -set 0.04 >/dev/null
mpirun --bind-to core -np 2 icoFoam -parallel > log.resumed 2>&1
grep -q '^End' log.resumed
if grep -Eqi 'FOAM FATAL|(^|[[:space:]])[-+]?nan([[:space:]]|$)' log.initial log.resumed; then exit 1; fi
for rank in 0 1; do
    for time in 0.02 0.04; do
        for field in U p phi; do test -s "processor$rank/$time/$field"; done
    done
done
python3 - "$root" "$(command -v icoFoam)" "$WM_PROJECT_VERSION" <<'PY'
import hashlib,json,re,sys
from pathlib import Path
from datetime import datetime
r=Path(sys.argv[1]);case=r/'case';p=json.loads((r/'checkpoint-before-resume.json').read_text())
for name,proof in p['files'].items():assert hashlib.sha256((case/name).read_bytes()).hexdigest()==proof['sha256']
times=[float(x) for x in re.findall(r'^Time = ([0-9.eE+-]+)',(case/'log.resumed').read_text(),re.M)]
assert times and min(times)>0.02 and max(times)>=0.04
result={'observed_at':datetime.now().astimezone().isoformat(),'solver':'icoFoam','version':sys.argv[3],
'solver_sha256':hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),'mpi_ranks':2,'omp_threads_per_rank':1,
'checkpoint_verified':True,'known_good_preserved':True,'resumed_from':0.02,'reached':max(times),
'resume_command':'source /usr/lib/openfoam/openfoam2512/etc/bashrc; mpirun --bind-to core -np 2 icoFoam -parallel',
'resume_configuration':{'startFrom':'latestTime','purgeWrite':0,'writeControl':'runTime','writeInterval':0.01},
'case':str(case),'functional_test_only':True,'production_case_qualified':False}
(r/'restart-verified.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
PY
