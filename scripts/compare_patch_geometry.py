#!/usr/bin/env python3
"""Compare OpenFOAM patch face counts, areas and normals from polyMesh."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import numpy as np

def entries(path: Path):
    text = path.read_text(errors="replace")
    body = text[text.find("(") + 1:text.rfind(")")]
    return body.splitlines()

def read_points(case: Path) -> np.ndarray:
    rows=[]
    for line in entries(case/"constant/polyMesh/points"):
        m=re.search(r"\(([-+0-9.eE ]+)\)",line)
        if m: rows.append([float(x) for x in m.group(1).split()])
    return np.asarray(rows,float)

def read_faces(case: Path):
    out=[]
    for line in entries(case/"constant/polyMesh/faces"):
        m=re.search(r"\(([-+0-9 ]+)\)",line)
        if m: out.append([int(x) for x in m.group(1).split()])
    return out

def patch_ranges(case: Path):
    s=(case/"constant/polyMesh/boundary").read_text(errors="replace")
    out={}
    for name, block in re.findall(r"\s*(\w+)\s*\{(.*?)\n\s*\}",s,re.S):
        nf=re.search(r"nFaces\s+(\d+)",block); st=re.search(r"startFace\s+(\d+)",block)
        if nf and st: out[name]=(int(st.group(1)),int(nf.group(1)))
    return out

def measure(case: Path):
    pts, faces = read_points(case), read_faces(case)
    out={}
    for name,(start,nf) in patch_ranges(case).items():
        areas=[]; normals=[]
        for face in faces[start:start+nf]:
            q=pts[face]; c=q.mean(0); av=np.zeros(3)
            for i in range(len(q)):
                av += np.cross(q[i]-c,q[(i+1)%len(q)]-c)/2
            areas.append(np.linalg.norm(av)); normals.append(av/(np.linalg.norm(av)+1e-30))
        out[name]={"faces":nf,"area":float(sum(areas)),"mean_normal":np.mean(normals,0).tolist()}
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--coarse",type=Path,required=True); ap.add_argument("--refined",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    c,r=measure(a.coarse),measure(a.refined); names=sorted(set(c)|set(r)); diff={}
    for n in names:
        if n in c and n in r:
            diff[n]={"coarse":c[n],"refined":r[n],"face_ratio":r[n]["faces"]/max(c[n]["faces"],1),"area_ratio":r[n]["area"]/max(c[n]["area"],1e-30)}
        else: diff[n]={"coarse":c.get(n),"refined":r.get(n),"status":"MISSING_PATCH"}
    report={"status":"PASS" if all("status" not in v and abs(v["area_ratio"]-1)<0.02 for v in diff.values()) else "REVIEW","patches":diff,"criterion":"area ratio within 2% and identical patch names"}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
