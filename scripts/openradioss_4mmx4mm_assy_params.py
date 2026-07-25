# -*- coding: utf-8 -*-
"""Apply DOE parameters to 4mmx4mm ASSY OpenRadioss deck (Punch/Die/Stripper/Material)."""

from __future__ import annotations

import sys
import math
import re
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
WS = ROOT / "data" / "workspace"
if str(WS) not in sys.path:
    sys.path.insert(0, str(WS))

import rad_model as rm

WORKPIECE_THICKNESS_MM = 0.5
DEFAULT_STROKE_MM = 2.0
# 2026-07-13 T060: 旧2500.0はDOE範囲[3000,6100](cae_workload_router.yaml 7/10是正)を
# 全trialで2500へ silent clamp し、範囲是正を無効化していた(8連敗の一因)。
# DOE上限に整合させ、clamp発動時は verify["punch_speed_clamped"]=True を記録する。
ASSY_MAX_PUNCH_SPEED_MMS = 6100.0
# 2026-07-13 T060: /DT/NODA/CST dt=1.0e-7 が本メッシュ自然dt(推定~1.7e-8)の約6倍で
# DM/M≈36-62倍(3600-6200%質量追加)→物理破綻の主因。8.0e-9で質量追加を10%未満へ抑える。
DEFAULT_DT_NODA_MIN = 8.0e-9
# t_stop はストローク通過時間ベース(旧: max(0.020, ...) の20ms床が
# gate MIN_T_MS=18.13ms と結合して「timeout内に完走不能」構造を作っていた)。
T_STOP_SAFETY = 1.4
T_STOP_MIN_S = 3.0e-4
ASSY_EXP_ID = "OR-BLANK-ASSY-001"
ASSY_CATEGORY = "press_blanking_assy"
ASSY_CASE_LABEL = "4mmx4mm_ASSY"


def _crank_displacement_points(
    *, spm: float, stroke_mm: float, target_mm: float, samples: int = 24
) -> tuple[list[tuple[float, float]], float]:
    """Return time/displacement points from TDC to the requested downstroke."""
    if spm <= 0.0 or stroke_mm <= 0.0:
        raise ValueError("spm and press_stroke_mm must be positive")
    if target_mm <= 0.0 or target_mm > stroke_mm:
        raise ValueError("target displacement must be in (0, press_stroke_mm]")
    radius_m = stroke_mm / 2000.0
    target_m = target_mm / 1000.0
    omega = 2.0 * math.pi * spm / 60.0
    end_angle = math.acos(1.0 - target_m / radius_m)
    end_time = end_angle / omega
    points: list[tuple[float, float]] = []
    for index in range(samples + 1):
        time_s = end_time * index / samples
        angle = omega * time_s
        displacement_m = -radius_m * (1.0 - math.cos(angle))
        points.append((time_s, displacement_m))
    return points, end_time


def _format_function(function_id: int, title: str, points: list[tuple[float, float]]) -> str:
    rows = "\n".join(f"{time_s:20.12E}{value:20.12E}" for time_s, value in points)
    return f"/FUNCT/{function_id}\n{title}\n#                  X                   Y\n{rows}"


def _replace_function(text: str, function_id: int, replacement: str) -> str:
    pattern = re.compile(
        rf"/FUNCT/{function_id}\s*\n.*?(?=\n/(?:FUNCT|IMPVEL|IMPDISP)/)",
        flags=re.DOTALL,
    )
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise ValueError(f"/FUNCT/{function_id} block not found")
    return updated


def _replace_impvel_with_impdisp(text: str, block_id: int, title: str, function_id: int, group_id: int) -> str:
    pattern = re.compile(
        rf"/IMPVEL/{block_id}\s*\n.*?(?=\n/(?:IMPVEL|IMPDISP|FAIL|INTER)/)",
        flags=re.DOTALL,
    )
    replacement = (
        f"/IMPDISP/{block_id}\n"
        f"{title}\n"
        "#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor\n"
        f"{function_id:10d}{'Z':>10}{0:10d}{0:10d}{group_id:10d}{0:10d}\n"
        "#             Ascale_x            Fscale_y              Tstart               Tstop\n"
        f"{1.0:20.5f}{1.0:20.5f}{0.0:20.5f}{1.0e30:20.5E}"
    )
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise ValueError(f"/IMPVEL/{block_id} block not found")
    return updated


def _apply_spm80_motion(starter_path: Path, params: dict) -> dict:
    spm = float(params["spm"])
    press_stroke_mm = float(params["press_stroke_mm"])
    punch_target_mm = float(params["punch_target_mm"])
    stripper_target_mm = float(params["stripper_target_mm"])
    punch_points, end_time = _crank_displacement_points(
        spm=spm,
        stroke_mm=press_stroke_mm,
        target_mm=punch_target_mm,
    )
    stripper_points = [
        (time_s, displacement_m * stripper_target_mm / punch_target_mm)
        for time_s, displacement_m in punch_points
    ]
    text = starter_path.read_text(encoding="utf-8", errors="replace")
    text = _replace_function(
        text,
        1,
        _format_function(1, "Punch_Crank_Displacement_SPM80", punch_points),
    )
    text = _replace_function(
        text,
        3,
        _format_function(3, "Stripper_Synchronized_Displacement", stripper_points),
    )
    text = _replace_impvel_with_impdisp(text, 1, "Punch_Displacement_Z", 1, 100)
    text = _replace_impvel_with_impdisp(text, 5, "Stripper_Displacement_Z", 3, 300)
    # The source deck used 0.05 m for TYPE25 die/stripper search gaps, which is
    # larger than the 4 mm model. Keep all tool/material searches local.
    local_gap_line = (
        f"{0:10d}{1.0:20.8E}{0.4:20.8E}"
        f"{4.0e-5:20.8E}{4.0e-5:20.8E}"
    )
    text = re.sub(
        r"(?m)^(\s*0\s+1\.0\s+0\.4\s+)0\.05(\s+)0\.05\s*$",
        local_gap_line,
        text,
    )
    starter_path.write_text(text, encoding="utf-8", newline="\n")
    return {
        "spm": spm,
        "press_stroke_mm": press_stroke_mm,
        "punch_target_mm": -punch_target_mm,
        "stripper_target_mm": -stripper_target_mm,
        "motion_end_s": end_time,
        "peak_press_speed_mms": math.pi * press_stroke_mm * spm / 60.0,
        "punch_end_speed_mms": (
            press_stroke_mm
            / 2.0
            * (2.0 * math.pi * spm / 60.0)
            * math.sin(2.0 * math.pi * spm / 60.0 * end_time)
        ),
    }


def is_assy_trial(params: dict | None, category: str = "", exp_id: str = "") -> bool:
    if exp_id == ASSY_EXP_ID or category == ASSY_CATEGORY:
        return True
    p = params or {}
    label = str(p.get("case_label") or "").strip()
    return label in {ASSY_CASE_LABEL, "4mmx4mm", "4mmx4mm_ASSY_20260105"}


def apply_assy_params(starter_path: Path, engine_path: Path, params: dict) -> dict:
    """Mutate starter/engine in place. Returns verify dict."""
    starter_path = starter_path.resolve()
    engine_path = engine_path.resolve()

    requested_speed_mms = float(params.get("punch_speed_mms") or 5000.0)
    punch_speed_mms = min(requested_speed_mms, ASSY_MAX_PUNCH_SPEED_MMS)
    speed_clamped = punch_speed_mms < requested_speed_mms
    friction_mu = float(params.get("friction_mu") or 0.10)
    clearance_pct = float(params.get("clearance_pct") or 8.0)
    dt_noda_min = float(params.get("dt_noda_min") or DEFAULT_DT_NODA_MIN)

    exact_motion = all(
        key in params
        for key in ("spm", "press_stroke_mm", "punch_target_mm", "stripper_target_mm")
    )
    motion_verify: dict = {}
    if exact_motion:
        motion_verify = _apply_spm80_motion(starter_path, params)
        t_stop = float(motion_verify["motion_end_s"])
    else:
        speed_m_s = punch_speed_mms / 1000.0
        stroke_m = DEFAULT_STROKE_MM / 1000.0
        t_stop = max(T_STOP_MIN_S, (stroke_m / max(speed_m_s, 0.05)) * T_STOP_SAFETY)
    gap_m = (clearance_pct / 100.0) * (WORKPIECE_THICKNESS_MM / 1000.0)
    gap_m = max(gap_m, 1.0e-5)

    model = rm.RadModel(starter_path)
    model.set_fail_gene1(eps_eff=0.35)
    model.set_inter_type25_idel(2)
    model.set_inter_type25_all(inacti=6, vc=0.35)
    model.set_inter_type25_penetration_fix()
    model.set_inter_type25_fric_all(friction_mu)
    model.set_inter_type25_gap_punch(gap_m)
    if not exact_motion:
        model.set_funct_y_plateau(1, -speed_m_s)
    model.write(starter_path)

    ams_applied = False
    dt_noda_applied = False
    if engine_path.exists():
        rm.set_engine_tstop(engine_path, t_stop)
        try:
            rm.set_engine_ams_scale(engine_path, 0.67)
            ams_applied = True
        except ValueError:
            # /DT/AMS ブロックが無いデッキでは silent no-op だった(T060)。実態を記録する。
            pass
        try:
            rm.set_engine_noda_dt_min(engine_path, dt_noda_min)
            dt_noda_applied = True
        except ValueError:
            pass

    verify = model.verify()
    verify.update(
        {
            "punch_speed_mms": punch_speed_mms,
            "punch_speed_requested_mms": requested_speed_mms,
            "punch_speed_clamped": speed_clamped,
            "friction_mu": friction_mu,
            "clearance_pct": clearance_pct,
            "gap_m": gap_m,
            "t_stop_s": t_stop,
            "speed_m_s": None if exact_motion else speed_m_s,
            "dt_noda_min": dt_noda_min,
            "dt_noda_applied": dt_noda_applied,
            "ams_applied": ams_applied,
            # gate用推奨値: 完走(NORMAL_TSTOP)なら t_final≈t_stop になるため 95% を要求
            "min_t_final_ms": round(t_stop * 1000.0 * 0.95, 3),
        }
    )
    verify.update(motion_verify)
    return verify
