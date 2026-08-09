# -*- coding: utf-8 -*-
"""Autonomous OpenRadioss DOE until gate T=18.13ms (NORMAL_TSTOP).

Phase A-E: HEX _orig VC/Eps sweep (legacy; plateau ~15.6ms at material rupture).
Phase F+: Run42-proven tetra path + HEX low-VC recovery + contact/AMS/TSTOP.

Stops on first gate pass. Logs to openradioss_sweep_results.jsonl + autonomous_status.json.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
WS = ROOT / "data" / "workspace"
sys.path.insert(0, str(WS))

import openradioss_hexmat_sweep as sw

GATE_MS = 18.13
JST = timezone(timedelta(hours=9))
STATUS = WS / "openradioss_autonomous_status.json"
LOG = WS / "openradioss_autonomous.log"
RESULTS = sw.RESULTS

# Run42 success: tetra, Eps=0.35, Inacti=6, VC=0.6, TSTOP=0.020 -> T=19.99ms NORMAL_TSTOP
RUN42 = {"mesh": "tetra", "vc": 0.6, "eps_eff": 0.35, "inacti": 6, "tstop": 0.025, "use_orig": False}

PHASE_ORDER = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]


def _log(msg: str) -> None:
    line = f"[{datetime.now(JST).strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _write_status(payload: dict) -> None:
    payload["updated_at_jst"] = datetime.now(JST).isoformat()
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _gate_pass(rec: dict) -> bool:
    t = rec.get("t_final_ms") or 0
    term = rec.get("termination", "")
    return float(t) >= GATE_MS and term == "NORMAL_TSTOP"


def _load_all_results() -> list[dict]:
    rows: list[dict] = []
    if not RESULTS.exists():
        return rows
    for line in RESULTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _load_best_t() -> tuple[float, dict | None]:
    best_t = 0.0
    best_rec = None
    for rec in _load_all_results():
        t = rec.get("t_final_ms") or 0
        if t and t > best_t:
            best_t = float(t)
            best_rec = rec
    return best_t, best_rec


def _load_hex_plateau_best() -> tuple[float, float]:
    """Best VC/Eps from completed HEX sweep (runs >= 150)."""
    best_t = 0.0
    best_vc, best_eps = 2.0, 0.37
    for rec in _load_all_results():
        if int(rec.get("run_id") or 0) < 150:
            continue
        if rec.get("mesh") == "tetra":
            continue
        t = rec.get("t_final_ms") or 0
        if t and float(t) >= best_t:
            best_t = float(t)
            best_vc = float(rec.get("vc") or best_vc)
            best_eps = float(rec.get("eps_eff") or best_eps)
    return best_vc, best_eps


def _run_case(case: sw.SweepCase) -> dict:
    rec = {"run_id": case.run_id, "label": case.label, "phase": case.label.split(":")[0], **asdict(case)}
    _log(f"Run{case.run_id} START: {case.label}")
    _write_status({"state": "running", "current_run": case.run_id, "label": case.label})
    try:
        sw.build_deck(case)
        ok, st_out = sw.run_starter()
        rec["starter_ok"] = ok
        if not ok:
            rec["status"] = "starter_fail"
            rec["starter_log"] = st_out[-400:]
            _log(f"Run{case.run_id} STARTER FAIL")
            return rec
        sw.start_engine(case.run_id)
        result = sw.wait_engine(case.run_id)
        rec.update(result)
        rec["status"] = "ok"
        rec["gate_passed"] = _gate_pass(rec)
        t = rec.get("t_final_ms", 0)
        _log(
            f"Run{case.run_id} DONE T={t}ms term={rec.get('termination')} "
            f"gate={'PASS' if rec['gate_passed'] else 'fail'}"
        )
    except Exception as exc:
        rec["status"] = "error"
        rec["error"] = str(exc)
        _log(f"Run{case.run_id} ERROR: {exc}")
    with RESULTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def _make_case(
    run_id: int,
    label: str,
    *,
    mesh: str = "hex",
    use_orig: bool = True,
    vc: float = 0.6,
    eps_eff: float = 0.3756,
    inacti: int = 6,
    tstop: float = 0.03,
    ams_scale: float | None = None,
    gap_max: float = 0.01,
    stfac_punch: float = 0.05,
    stfac_die: float = 1e-4,
    stfac_strip: float = 1e-4,
) -> sw.SweepCase:
    return sw.SweepCase(
        run_id=run_id,
        label=label,
        mesh=mesh,
        isolid=24,
        inacti=inacti,
        vc=vc,
        eps_eff=eps_eff,
        tstop=tstop,
        ams_scale=ams_scale,
        use_orig=use_orig,
        gap_max=gap_max,
        stfac_punch=stfac_punch,
        stfac_die=stfac_die,
        stfac_strip=stfac_strip,
    )


def _check_gate(recs: list[dict], run_id: int) -> tuple[bool, int]:
    if any(_gate_pass(r) for r in recs):
        hit = next(r for r in recs if _gate_pass(r))
        _write_status({"state": "success", "gate_ms": GATE_MS, "success_run": hit})
        _log(f"GATE PASS Run{hit['run_id']} T={hit['t_final_ms']}ms term={hit.get('termination')}")
        return True, run_id
    return False, run_id


def phase_a_vc(run_start: int) -> tuple[list[dict], int, float, float]:
    vcs = [1.3, 1.4, 1.5, 1.687, 2.0, 2.5]
    records: list[dict] = []
    best_vc = 1.2
    best_t = 15.0
    rid = run_start
    for vc in vcs:
        rec = _run_case(_make_case(rid, f"A:VC={vc}", vc=vc, use_orig=True))
        records.append(rec)
        t = rec.get("t_final_ms") or 0
        if t > best_t:
            best_t, best_vc = float(t), vc
        ok, rid = _check_gate(records, rid + 1)
        if ok:
            return records, rid, best_vc, best_t
        rid += 1
    return records, rid, best_vc, best_t


def phase_b_eps(run_start: int, vc: float) -> tuple[list[dict], int, float, float]:
    eps_list = [0.33, 0.35, 0.37, 0.40, 0.42]
    records: list[dict] = []
    best_eps = 0.3756
    best_t = 0.0
    rid = run_start
    for eps in eps_list:
        rec = _run_case(_make_case(rid, f"B:VC={vc} Eps={eps}", vc=vc, eps_eff=eps, use_orig=True))
        records.append(rec)
        t = rec.get("t_final_ms") or 0
        if t > best_t:
            best_t, best_eps = float(t), eps
        ok, rid = _check_gate(records, rid + 1)
        if ok:
            return records, rid + 1, best_eps, best_t
        rid += 1
    return records, rid, best_eps, best_t


def phase_c_dopt(run_start: int, vc0: float, eps0: float) -> tuple[list[dict], int]:
    points = [
        (vc0, eps0),
        (vc0 + 0.15, eps0),
        (vc0 - 0.10, eps0),
        (vc0, eps0 - 0.03),
        (vc0, eps0 + 0.03),
        (vc0 + 0.10, eps0 - 0.02),
        (vc0 + 0.10, eps0 + 0.02),
    ]
    seen: set[tuple[float, float]] = set()
    records: list[dict] = []
    rid = run_start
    for vc, eps in points:
        key = (round(vc, 4), round(eps, 4))
        if key in seen:
            continue
        seen.add(key)
        vc = max(0.5, min(vc, 3.0))
        eps = max(0.25, min(eps, 0.50))
        rec = _run_case(
            _make_case(rid, f"C:VC={vc:.3f} Eps={eps:.3f}", vc=vc, eps_eff=eps, use_orig=True)
        )
        records.append(rec)
        ok, rid = _check_gate(records, rid + 1)
        if ok:
            return records, rid
        rid += 1
    return records, rid


def phase_d_ams(run_start: int, vc: float, eps: float) -> tuple[list[dict], int]:
    scales = [0.55, 0.67, 0.85]
    records: list[dict] = []
    rid = run_start
    for sc in scales:
        rec = _run_case(
            _make_case(
                rid,
                f"D:AMS={sc} VC={vc} Eps={eps}",
                vc=vc,
                eps_eff=eps,
                ams_scale=sc,
                use_orig=True,
            )
        )
        records.append(rec)
        ok, rid = _check_gate(records, rid + 1)
        if ok:
            return records, rid
        rid += 1
    return records, rid


def phase_e_tstop(run_start: int, vc: float, eps: float) -> tuple[list[dict], int]:
    tstops = [0.032, 0.034, 0.035, 0.040]
    records: list[dict] = []
    rid = run_start
    for ts in tstops:
        rec = _run_case(
            _make_case(rid, f"E:TSTOP={ts} VC={vc} Eps={eps}", vc=vc, eps_eff=eps, tstop=ts, use_orig=True)
        )
        records.append(rec)
        ok, rid = _check_gate(records, rid + 1)
        if ok:
            return records, rid
        rid += 1
    return records, rid


def phase_f_run42_tetra(run_start: int) -> tuple[list[dict], int]:
    """Reproduce Run42 proven settings on tetra mesh."""
    records: list[dict] = []
    rid = run_start
    cases = [
        ("F:Run42 tetra baseline", 0.35, 0.025),
        ("F:Run42 tetra TSTOP=0.020", 0.35, 0.020),
        ("F:Run42 tetra TSTOP=0.028", 0.35, 0.028),
    ]
    for label, eps, ts in cases:
        rec = _run_case(
            _make_case(
                rid,
                label,
                mesh="tetra",
                use_orig=False,
                vc=RUN42["vc"],
                eps_eff=eps,
                inacti=RUN42["inacti"],
                tstop=ts,
            )
        )
        records.append(rec)
        ok, rid = _check_gate(records, rid + 1)
        if ok:
            return records, rid
        rid += 1
    return records, rid


def phase_g_tetra_fine(run_start: int) -> tuple[list[dict], int]:
    records: list[dict] = []
    rid = run_start
    for eps in [0.33, 0.34, 0.35, 0.36, 0.37]:
        for vc in [0.5, 0.6, 0.7]:
            rec = _run_case(
                _make_case(
                    rid,
                    f"G:tetra VC={vc} Eps={eps}",
                    mesh="tetra",
                    use_orig=False,
                    vc=vc,
                    eps_eff=eps,
                    inacti=6,
                    tstop=0.025,
                )
            )
            records.append(rec)
            ok, rid = _check_gate(records, rid + 1)
            if ok:
                return records, rid
            rid += 1
    return records, rid


def phase_h_hex_run42_params(run_start: int) -> tuple[list[dict], int]:
    """HEX with Run42-like low VC (high VC caused rupture plateau ~15.6ms)."""
    records: list[dict] = []
    rid = run_start
    for vc in [0.6, 0.8, 1.0, 1.2]:
        for eps in [0.33, 0.35, 0.37]:
            rec = _run_case(
                _make_case(
                    rid,
                    f"H:hex VC={vc} Eps={eps}",
                    mesh="hex",
                    use_orig=True,
                    vc=vc,
                    eps_eff=eps,
                    inacti=6,
                    tstop=0.025,
                )
            )
            records.append(rec)
            ok, rid = _check_gate(records, rid + 1)
            if ok:
                return records, rid
            rid += 1
    return records, rid


def phase_i_soft_contact(run_start: int, vc: float, eps: float, mesh: str) -> tuple[list[dict], int]:
    records: list[dict] = []
    rid = run_start
    combos = [
        (0.005, 2e-2, 5e-5, 5e-5, "soft-A"),
        (0.008, 3e-2, 8e-5, 8e-5, "soft-B"),
    ]
    use_orig = mesh != "tetra"
    for gap, sp, sd, ss, tag in combos:
        rec = _run_case(
            _make_case(
                rid,
                f"I:{tag} {mesh} VC={vc} Eps={eps}",
                mesh=mesh,
                use_orig=use_orig,
                vc=vc,
                eps_eff=eps,
                tstop=0.028,
                gap_max=gap,
                stfac_punch=sp,
                stfac_die=sd,
                stfac_strip=ss,
            )
        )
        records.append(rec)
        ok, rid = _check_gate(records, rid + 1)
        if ok:
            return records, rid
        rid += 1
    return records, rid


def phase_j_combo_push(run_start: int, vc: float, eps: float, mesh: str) -> tuple[list[dict], int]:
    records: list[dict] = []
    rid = run_start
    use_orig = mesh != "tetra"
    for sc in [0.55, 0.67, 0.85]:
        for ts in [0.030, 0.035, 0.040, 0.045]:
            rec = _run_case(
                _make_case(
                    rid,
                    f"J:AMS={sc} TSTOP={ts} {mesh}",
                    mesh=mesh,
                    use_orig=use_orig,
                    vc=vc,
                    eps_eff=eps,
                    tstop=ts,
                    ams_scale=sc,
                )
            )
            records.append(rec)
            ok, rid = _check_gate(records, rid + 1)
            if ok:
                return records, rid
            rid += 1
    return records, rid


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Autonomous OpenRadioss until gate T=18.13ms")
    ap.add_argument("--start-run", type=int, default=0, help="Override first run id")
    ap.add_argument(
        "--from-phase",
        default="F",
        help="First phase to run (A..J). Default F skips completed HEX plateau sweep.",
    )
    ap.add_argument("--only-phase", default="", help="Run single phase letter only")
    args = ap.parse_args()

    if not sw.ORIG_STARTER.exists():
        _log("promoting Run111 to _orig.rad ...")
        sw.promote_run111_to_orig()

    best_t, _ = _load_best_t()
    run_id = 174
    if args.start_run > 0:
        run_id = args.start_run
    else:
        for rec in _load_all_results():
            rid = int(rec.get("run_id") or 0)
            if rid >= run_id:
                run_id = rid + 1

    from_phase = (args.from_phase or "F").upper()
    if from_phase not in PHASE_ORDER:
        print(f"[NG] unknown phase {from_phase}", file=sys.stderr)
        return 1
    if args.only_phase:
        phases = [args.only_phase.upper()]
    else:
        phases = PHASE_ORDER[PHASE_ORDER.index(from_phase) :]

    hex_vc, hex_eps = _load_hex_plateau_best()
    _write_status(
        {
            "state": "running",
            "mode": "autonomous_until_gate_v2",
            "gate_ms": GATE_MS,
            "prior_best_ms": best_t,
            "hex_plateau_vc": hex_vc,
            "hex_plateau_eps": hex_eps,
            "plan": phases,
            "next_run_id": run_id,
            "run42_reference": RUN42,
        }
    )
    _log(
        f"=== autonomous v2 gate {GATE_MS}ms from Run{run_id} "
        f"(prior best {best_t}ms, phases={','.join(phases)}) ==="
    )
    _log(f"HEX plateau VC={hex_vc} Eps={hex_eps} -- Phase F+ uses Run42 tetra path")

    all_recs: list[dict] = []

    for phase in phases:
        if phase == "A":
            _log("--- Phase A: VC line search (HEX) ---")
            recs, run_id, best_vc, _ = phase_a_vc(run_id)
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0
            hex_vc = best_vc
        elif phase == "B":
            _log(f"--- Phase B: Eps_eff at VC={hex_vc} ---")
            recs, run_id, best_eps, _ = phase_b_eps(run_id, hex_vc)
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0
            hex_eps = best_eps
        elif phase == "C":
            _log(f"--- Phase C: 2D D-opt VC={hex_vc} Eps={hex_eps} ---")
            recs, run_id = phase_c_dopt(run_id, hex_vc, hex_eps)
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0
        elif phase == "D":
            _log(f"--- Phase D: AMS VC={hex_vc} Eps={hex_eps} ---")
            recs, run_id = phase_d_ams(run_id, hex_vc, hex_eps)
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0
        elif phase == "E":
            _log(f"--- Phase E: TSTOP VC={hex_vc} Eps={hex_eps} ---")
            recs, run_id = phase_e_tstop(run_id, hex_vc, hex_eps)
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0
        elif phase == "F":
            _log("--- Phase F: Run42 tetra reproduction ---")
            recs, run_id = phase_f_run42_tetra(run_id)
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0
        elif phase == "G":
            _log("--- Phase G: tetra VC x Eps fine ---")
            recs, run_id = phase_g_tetra_fine(run_id)
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0
        elif phase == "H":
            _log("--- Phase H: HEX Run42-like low VC ---")
            recs, run_id = phase_h_hex_run42_params(run_id)
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0
        elif phase == "I":
            _log("--- Phase I: soft contact (tetra Run42 + hex best) ---")
            recs, run_id = phase_i_soft_contact(run_id, RUN42["vc"], RUN42["eps_eff"], "tetra")
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0
            recs, run_id = phase_i_soft_contact(run_id, 0.6, 0.35, "hex")
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0
        elif phase == "J":
            _log("--- Phase J: AMS x TSTOP push ---")
            recs, run_id = phase_j_combo_push(run_id, RUN42["vc"], RUN42["eps_eff"], "tetra")
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0
            recs, run_id = phase_j_combo_push(run_id, 0.6, 0.35, "hex")
            all_recs.extend(recs)
            ok, run_id = _check_gate(recs, run_id)
            if ok:
                return 0

    peak = max((r.get("t_final_ms") or 0) for r in all_recs) or best_t
    _write_status(
        {
            "state": "paused",
            "gate_ms": GATE_MS,
            "peak_t_ms": peak,
            "message": "Phases done without gate; tetra Run42 path + HEX low-VC exhausted",
            "last_run_id": run_id - 1,
        }
    )
    _log(f"STOPPED peak T={peak}ms < gate {GATE_MS}ms")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
