"""
TherbligLabeler — Geometry-based Therblig classification from MediaPipe pose data.

Replaces the former template-cycling approach with actual feature extraction.

Detected Therbligs (from skeleton geometry alone):
  TE  Transport Empty   — fast hand movement, low approach deceleration
  TL  Transport Loaded  — moderate speed, consistent direction, wrist below shoulder
  G   Grasp             — slow decelerating approach to a point
  RL  Release Load      — rapid departure from hold position
  P   Position          — very slow, high-precision final approach (high decel + low variance)
  H   Hold              — primary hand stationary, other hand active
  UDe Unavoidable Delay — both hands stationary (machine/process wait)
  ADe Avoidable Delay   — both hands stationary (worker-caused)
  I   Inspect           — slow hand near head/face level, low velocity
  U   Use               — repetitive oscillating / tool motion
  B   Body Motion       — trunk bend or body repositioning

MOST (BasicMOST) indices estimated from geometry:
  A (distance)  ← hand travel distance calibrated via body height
  B (body)      ← trunk bend magnitude
  G (grasp)     ← approach deceleration profile
  P (place)     ← end-of-motion velocity variance
"""
import math
import numpy as np

# ── Therblig definitions ──────────────────────────────────────────────────────
THERBLIGS = {
    "TE":   ("Transport Empty",    False),
    "TL":   ("Transport Loaded",   False),
    "G":    ("Grasp",              False),
    "RL":   ("Release Load",       False),
    "P":    ("Position",           False),
    "H":    ("Hold",               True),   # NVA
    "UDe":  ("Unavoidable Delay",  True),   # NVA
    "ADe":  ("Avoidable Delay",    True),   # NVA
    "I":    ("Inspect",            False),
    "U":    ("Use",                False),
    "B":    ("Body Motion",        False),
    # Legacy / fallback
    "GET":    ("Get",              False),
    "PUT":    ("Put",              False),
    "MOVE":   ("Move",             False),
    "WAIT":   ("Wait (Delay)",     True),
    "INSPECT": ("Inspect",         False),
    "RECORD":  ("Record",          False),
    "SEARCH":  ("Search",          True),
    "USE_TOOL": ("Use Tool",       False),
    "POSITION": ("Position",       False),
}


class TherbligLabeler:
    def __init__(self, template: dict):
        self.template      = template
        self.expected_flow = template.get("expected_flow", [])

    def label(self, segments: list[dict], pose_data: list[dict]) -> list[dict]:
        """
        Classify each segment into a Therblig using geometric features.
        Falls back to template expected_flow when pose data is insufficient.
        Each label includes a `confidence` score (0.0–1.0).
        """
        fps        = pose_data[0].get("fps", 30.0) if pose_data else 30.0
        body_scale = self._estimate_body_scale(pose_data)

        labeled    = []
        prev_label = None

        for idx, seg in enumerate(segments):
            s, e  = seg["start_frame"], seg["end_frame"]
            dur   = seg["end_sec"] - seg["start_sec"]
            feats = self._extract_features(pose_data, s, e, fps)

            therblig, base_conf = self._classify(feats, dur, prev_label, idx)

            # Visibility ratio: fraction of segment frames where wrist was detected
            vis_ratio  = feats["n_r_wrist"] / max(feats["n_frames"], 1)
            # Confidence = rule base × visibility quality (floor 0.20 so low-vis still classifies)
            confidence = round(base_conf * max(0.20, vis_ratio), 3)

            desc, is_nva = THERBLIGS.get(therblig, (therblig, False))
            most         = self._estimate_most_indices(feats, body_scale, therblig)

            labeled.append({
                "segment_id":   idx,
                "start_frame":  s,
                "end_frame":    e,
                "start_sec":    seg["start_sec"],
                "end_sec":      seg["end_sec"],
                "label":        therblig,
                "label_jp":     _JP.get(therblig, desc),
                "duration_sec": round(dur, 2),
                "avg_velocity": round(feats["avg_vel"], 4),
                "is_nva":       is_nva,
                "confidence":   confidence,
                "vis_ratio":    round(vis_ratio, 3),
                # MOST index estimates
                "most_A":       most["A"],
                "most_B":       most["B"],
                "most_G":       most["G"],
                "most_P":       most["P"],
                "most_tmu":     most["tmu"],
            })
            prev_label = therblig

        return labeled

    # ── Feature extraction ────────────────────────────────────────────────────

    def _extract_features(self, pose_data, s, e, fps) -> dict:
        """Extract geometric motion features from a pose segment."""
        frames = pose_data[s : e + 1]
        if not frames:
            return _empty_features()

        # Gather per-frame landmarks
        r_wrist = []   # landmark 16
        l_wrist = []   # landmark 15
        r_elbow = []   # landmark 14
        nose    = []   # landmark 0
        r_hip   = []   # landmark 24
        l_hip   = []   # landmark 23
        r_shou  = []   # landmark 12
        trunk_angs = []

        for f in frames:
            lms = f.get("landmarks", [])
            n   = len(lms)
            def lm(i): return (lms[i]["x"], lms[i]["y"]) if n > i and lms[i]["visibility"] > 0.3 else None

            rw, lw = lm(16), lm(15)
            if rw: r_wrist.append(rw)
            if lw: l_wrist.append(lw)
            re = lm(14); re and r_elbow.append(re)
            nd = lm(0);  nd and nose.append(nd)
            rs = lm(12); rs and r_shou.append(rs)
            rh, lh = lm(24), lm(23)
            if rh: r_hip.append(rh)

            # Trunk lean: angle of nose→hip midpoint vector from vertical
            if nd and rh and lh:
                mx = (lms[23]["x"] + lms[24]["x"]) / 2
                my = (lms[23]["y"] + lms[24]["y"]) / 2
                dx, dy = nd[0] - mx, nd[1] - my
                if abs(dy) > 1e-6:
                    trunk_angs.append(math.degrees(math.atan2(abs(dx), abs(dy))))

        def velocities(pts):
            if len(pts) < 2:
                return np.array([0.0])
            return np.array([
                math.hypot(pts[i][0]-pts[i-1][0], pts[i][1]-pts[i-1][1])
                for i in range(1, len(pts))
            ])

        r_vel = velocities(r_wrist)
        l_vel = velocities(l_wrist)

        avg_vel = float(np.mean(r_vel))
        max_vel = float(np.max(r_vel))

        # Approach deceleration: compare first-half vs last-quarter velocities
        if len(r_vel) >= 6:
            q  = max(2, len(r_vel) // 4)
            approach_decel = float(np.mean(r_vel[:q]) - np.mean(r_vel[-q:]))
            end_variance   = float(np.var(r_vel[-q:]))
        else:
            approach_decel = 0.0
            end_variance   = 0.0

        # Travel distance
        travel = float(np.sum(r_vel))

        # Bilateral: is left hand moving while right is still?
        l_avg = float(np.mean(l_vel))

        # Hand height vs shoulder
        hand_above_shou = False
        if r_wrist and r_shou:
            hand_above_shou = r_wrist[-1][1] < r_shou[-1][1]  # y inverted

        # Oscillation: direction reversals in right wrist
        reversals = 0
        if len(r_wrist) > 4:
            xs = [p[0] for p in r_wrist]
            for i in range(2, len(xs)):
                if (xs[i]-xs[i-1]) * (xs[i-1]-xs[i-2]) < 0:
                    reversals += 1

        return {
            "avg_vel":        avg_vel,
            "max_vel":        max_vel,
            "approach_decel": approach_decel,
            "end_variance":   end_variance,
            "travel":         travel,
            "l_avg_vel":      l_avg,
            "hand_above_shou": hand_above_shou,
            "trunk_bend":     float(np.mean(trunk_angs)) if trunk_angs else 0.0,
            "oscillations":   reversals,
            "n_r_wrist":      len(r_wrist),
            "n_frames":       len(frames),
        }

    def _classify(
        self, f: dict, dur: float, prev: str | None, idx: int
    ) -> tuple[str, float]:
        """
        Rule-based Therblig classification from geometric features.

        Returns:
            (therblig_label, base_confidence)

        base_confidence: how "cleanly" the rule fired (0.25 – 0.95).
        Final confidence is scaled by visibility ratio in the caller.

        Confidence levels reflect rule specificity:
          0.88–0.95  Both-hands signals    (UDe/ADe/H)     — very reliable
          0.75–0.87  Strong geometry       (B/U/I)          — clear signal
          0.62–0.74  Multi-condition rules (P/G/RL/TL)      — moderate
          0.50–0.61  Single velocity rule  (TE)             — weakest geometric
          0.25       Template fallback                      — no geometry support
        """
        av  = f["avg_vel"]
        mv  = f["max_vel"]
        dec = f["approach_decel"]
        var = f["end_variance"]
        osc = f["oscillations"]
        tb  = f["trunk_bend"]

        # ── Delay / Wait ─────────────────────────────────────────────────────
        if av < 0.004 and f["l_avg_vel"] < 0.004:
            # Bilateral stillness: very reliable; confidence scales with how still
            margin = 1.0 - (av + f["l_avg_vel"]) / 0.008   # 0→1 as stillness increases
            return ("UDe" if dur > 2.0 else "ADe"), min(0.95, 0.80 + margin * 0.15)

        # ── Hold: right still, left moving ───────────────────────────────────
        if av < 0.006 and f["l_avg_vel"] > 0.015:
            contrast = min(1.0, f["l_avg_vel"] / 0.06)     # stronger contrast → higher conf
            return "H", min(0.92, 0.72 + contrast * 0.20)

        # ── Body motion ───────────────────────────────────────────────────────
        if tb > 20 and av < 0.02:
            bend_margin = min(1.0, (tb - 20) / 30)         # how far above 20° threshold
            return "B", min(0.88, 0.68 + bend_margin * 0.20)

        # ── Inspect: slow, near face/head level ──────────────────────────────
        if av < 0.012 and f["hand_above_shou"] and dur > 0.5:
            slowness = min(1.0, (0.012 - av) / 0.012)
            return "I", min(0.82, 0.60 + slowness * 0.22)

        # ── Use (tool): oscillating motion ───────────────────────────────────
        if osc > max(3, dur * 4) and av > 0.01:
            osc_margin = min(1.0, osc / max(dur * 8, 4))   # denser oscillation → higher conf
            return "U", min(0.85, 0.65 + osc_margin * 0.20)

        # ── Position: very slow, decelerating, low variance at end ───────────
        if av < 0.018 and dec > 0.005 and var < 0.0002:
            # Three conditions must all fire
            cond_score = (
                min(1.0, (0.018 - av) / 0.018) * 0.4 +
                min(1.0, dec / 0.015)           * 0.3 +
                min(1.0, (0.0002 - var) / 0.0002) * 0.3
            )
            return "P", min(0.80, 0.55 + cond_score * 0.25)

        # ── Grasp: decelerating approach, moderate speed ──────────────────────
        if 0.008 < av < 0.04 and dec > 0.006 and prev in (None, "TE", "TL", "B"):
            vel_score = 1.0 - abs(av - 0.024) / 0.016      # peak conf near av=0.024
            dec_score = min(1.0, dec / 0.02)
            return "G", min(0.78, 0.52 + (vel_score * 0.5 + dec_score * 0.5) * 0.26)

        # ── Release Load: quick departure, after G or H ──────────────────────
        if av > 0.02 and dec < 0 and prev in ("G", "H", "P", "U"):
            dep_score = min(1.0, av / 0.05)
            return "RL", min(0.75, 0.50 + dep_score * 0.25)

        # ── Transport (high velocity) ─────────────────────────────────────────
        if mv > 0.04:
            vel_score = min(1.0, (mv - 0.04) / 0.06)       # higher speed → more confident
            if prev in ("G", "H", "U"):
                return "TL", min(0.72, 0.52 + vel_score * 0.20)
            return "TE", min(0.65, 0.45 + vel_score * 0.20)

        # ── Fallback: template expected_flow cycling (no geometry support) ────
        if self.expected_flow:
            return self.expected_flow[idx % len(self.expected_flow)], 0.25
        return "TE", 0.25

    # ── MOST index estimation ─────────────────────────────────────────────────

    def _estimate_most_indices(self, f: dict, body_scale: float, therblig: str) -> dict:
        """
        Estimate BasicMOST indices from geometric features.
        body_scale: normalized units per 100cm (from body height calibration).
        """
        # A-index (Action distance): from hand travel
        travel_cm = (f["travel"] / body_scale * 100) if body_scale > 0 else 0
        A = _a_index(travel_cm)

        # B-index (Body motion): trunk bend
        tb = f["trunk_bend"]
        B = 6 if tb > 35 else (3 if tb > 15 else 0)

        # G-index (Grasp control): from approach deceleration
        dec = f["approach_decel"]
        G = 3 if dec > 0.015 else (1 if dec > 0.005 else 0)
        if therblig in ("TE", "TL", "MOVE"):
            G = 0   # no grasp in transport

        # P-index (Placement): from end variance and deceleration
        var = f["end_variance"]
        dec2 = f["approach_decel"]
        if therblig in ("P", "PUT", "POSITION"):
            P = 6 if var < 0.00005 and dec2 > 0.01 else (3 if dec2 > 0.004 else 1)
        elif therblig in ("G", "GET"):
            P = 0
        else:
            P = 1 if f["avg_vel"] < 0.015 else 0

        # General Move sequence for this motion: A-B-G-A-B-P-A (simplified)
        # Simplified TMU = (A + B + G + A + B + P + A) × 10  where A appears 3 times
        tmu = (A + B + G + A + B + P + A) * 10   # TMU (1 TMU = 0.036 s)

        return {"A": A, "B": B, "G": G, "P": P, "tmu": tmu}

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _estimate_body_scale(pose_data: list[dict]) -> float:
        """
        Estimate pixels-per-100cm from person's height in normalized coordinates.
        Uses nose (0) to midpoint of hips (23, 24) as ~60% of body height (~102cm).
        """
        heights = []
        for f in pose_data[:min(100, len(pose_data))]:
            lms = f.get("landmarks", [])
            if len(lms) < 25:
                continue
            nose = lms[0]
            hip_y = (lms[23]["y"] + lms[24]["y"]) / 2
            if nose["visibility"] > 0.5 and lms[23]["visibility"] > 0.5:
                heights.append(abs(nose["y"] - hip_y))
        if not heights:
            return 0.005   # fallback: ~200px per 100cm in normalized coords
        # ~102cm represented by avg height
        return float(np.median(heights)) / 102 * 100   # scale per 100cm


# ── MOST A-index distance table ───────────────────────────────────────────────
def _a_index(travel_cm: float) -> int:
    if travel_cm < 5:   return 0
    if travel_cm < 30:  return 1
    if travel_cm < 80:  return 3
    if travel_cm < 200: return 6
    if travel_cm < 500: return 10
    return 16


def _empty_features() -> dict:
    return {
        "avg_vel": 0, "max_vel": 0, "approach_decel": 0,
        "end_variance": 0, "travel": 0, "l_avg_vel": 0,
        "hand_above_shou": False, "trunk_bend": 0,
        "oscillations": 0, "n_r_wrist": 0, "n_frames": 1,
    }


# ── Japanese labels ───────────────────────────────────────────────────────────
_JP = {
    "TE":   "空運び (TE)",
    "TL":   "負荷運び (TL)",
    "G":    "つかむ (G)",
    "RL":   "放す (RL)",
    "P":    "位置決め (P)",
    "H":    "保持 (H)",
    "UDe":  "不可避遅延 (UDe)",
    "ADe":  "可避遅延 (ADe)",
    "I":    "検査 (I)",
    "U":    "使用 (U)",
    "B":    "身体動作 (B)",
    "GET":  "取る",
    "PUT":  "置く",
    "MOVE": "移動",
    "WAIT": "待ち",
    "INSPECT": "検査",
    "RECORD":  "記録",
    "SEARCH":  "探す",
    "USE_TOOL": "道具使用",
    "POSITION": "位置決め",
}
