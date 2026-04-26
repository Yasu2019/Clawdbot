"""
TherbligLabeler - geometry-based Therblig classification from MediaPipe pose data.

This version improves stability over the older threshold ladder by:
- using both wrists instead of only the right wrist
- scoring every Therblig candidate from multiple cues
- exposing low-confidence / review-required segments instead of hiding them
- applying a small temporal smoothing pass to suppress isolated spikes
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np


THERBLIGS = {
    "TE": ("Transport Empty", False),
    "TL": ("Transport Loaded", False),
    "G": ("Grasp", False),
    "RL": ("Release Load", False),
    "P": ("Position", False),
    "H": ("Hold", True),
    "UDe": ("Unavoidable Delay", True),
    "ADe": ("Avoidable Delay", True),
    "I": ("Inspect", False),
    "U": ("Use", False),
    "B": ("Body Motion", False),
    "UNKNOWN": ("Review Required", False),
    # Legacy / compatibility labels used by some templates and reports
    "GET": ("Get", False),
    "PUT": ("Put", False),
    "MOVE": ("Move", False),
    "WAIT": ("Wait (Delay)", True),
    "INSPECT": ("Inspect", False),
    "RECORD": ("Record", False),
    "SEARCH": ("Search", True),
    "USE_TOOL": ("Use Tool", False),
    "POSITION": ("Position", False),
}

_JP = {
    "TE": "運搬空手 (TE)",
    "TL": "運搬負荷 (TL)",
    "G": "つかむ (G)",
    "RL": "手放す (RL)",
    "P": "位置決め (P)",
    "H": "保持 (H)",
    "UDe": "不可避遅れ (UDe)",
    "ADe": "可避遅れ (ADe)",
    "I": "検査 (I)",
    "U": "使用 (U)",
    "B": "身体動作 (B)",
    "UNKNOWN": "要確認 (UNKNOWN)",
    "GET": "取る",
    "PUT": "置く",
    "MOVE": "移動",
    "WAIT": "待ち",
    "INSPECT": "検査",
    "RECORD": "記録",
    "SEARCH": "探す",
    "USE_TOOL": "道具使用",
    "POSITION": "位置決め",
}

_SCORABLE_LABELS = ("UDe", "ADe", "H", "B", "I", "U", "P", "G", "RL", "TL", "TE")
_TRANSPORT_LABELS = {"TE", "TL"}
_RELEASE_PREV = {"G", "H", "P", "U", "TL"}
_LOW_CONFIDENCE = 0.45
_REVIEW_THRESHOLD = 0.38


class TherbligLabeler:
    def __init__(self, template: dict):
        self.template = template
        self.expected_flow = template.get("expected_flow", [])

    def label(self, segments: list[dict], pose_data: list[dict]) -> list[dict]:
        fps = pose_data[0].get("fps", 30.0) if pose_data else 30.0
        body_scale = self._estimate_body_scale(pose_data)

        preliminary: list[dict] = []
        prev_label: str | None = None

        for idx, seg in enumerate(segments):
            s = seg["start_frame"]
            e = seg["end_frame"]
            dur = seg["end_sec"] - seg["start_sec"]
            feats = self._extract_features(pose_data, s, e, fps)
            classification = self._classify(feats, dur, prev_label, idx)

            label = classification["label"]
            confidence = classification["confidence"]
            desc, is_nva = THERBLIGS.get(label, (label, False))
            most = self._estimate_most_indices(feats, body_scale, label)

            record = {
                "segment_id": idx,
                "start_frame": s,
                "end_frame": e,
                "start_sec": seg["start_sec"],
                "end_sec": seg["end_sec"],
                "label": label,
                "label_jp": _JP.get(label, desc),
                "duration_sec": round(dur, 2),
                "avg_velocity": round(feats["active_avg_vel"], 4),
                "is_nva": is_nva,
                "confidence": confidence,
                "vis_ratio": round(feats["vis_ratio"], 3),
                "review_required": confidence < _LOW_CONFIDENCE or label == "UNKNOWN",
                "review_reason": classification["review_reason"],
                "score_gap": round(classification["score_gap"], 3),
                "score_detail": classification["scores"],
                "evidence": classification["evidence"],
                "most_A": most["A"],
                "most_B": most["B"],
                "most_G": most["G"],
                "most_P": most["P"],
                "most_tmu": most["tmu"],
            }
            preliminary.append(record)
            prev_label = label

        smoothed = self._smooth_labels(preliminary)
        self._refresh_most_fields(smoothed, body_scale, [self._extract_features(
            pose_data, seg["start_frame"], seg["end_frame"], fps
        ) for seg in segments])
        return smoothed

    def _extract_features(self, pose_data: list[dict], s: int, e: int, fps: float) -> dict:
        frames = pose_data[s: e + 1]
        if not frames:
            return _empty_features()

        right_wrist = []
        left_wrist = []
        right_shoulder = []
        left_shoulder = []
        nose = []
        hips = []
        trunk_angles = []
        wrist_spread = []

        for frame in frames:
            lms = frame.get("landmarks", [])
            n = len(lms)

            def lm(i: int):
                if n <= i:
                    return None
                item = lms[i]
                if item.get("visibility", 0.0) <= 0.3:
                    return None
                return (item["x"], item["y"])

            rw = lm(16)
            lw = lm(15)
            rs = lm(12)
            ls = lm(11)
            nd = lm(0)
            rh = lm(24)
            lh = lm(23)

            if rw:
                right_wrist.append(rw)
            if lw:
                left_wrist.append(lw)
            if rs:
                right_shoulder.append(rs)
            if ls:
                left_shoulder.append(ls)
            if nd:
                nose.append(nd)
            if rh and lh:
                hip_mid = ((rh[0] + lh[0]) / 2, (rh[1] + lh[1]) / 2)
                hips.append(hip_mid)
                if nd:
                    dx = nd[0] - hip_mid[0]
                    dy = nd[1] - hip_mid[1]
                    if abs(dy) > 1e-6:
                        trunk_angles.append(math.degrees(math.atan2(abs(dx), abs(dy))))
            if rw and lw:
                wrist_spread.append(math.hypot(rw[0] - lw[0], rw[1] - lw[1]))

        def velocities(points: list[tuple[float, float]]) -> np.ndarray:
            if len(points) < 2:
                return np.array([0.0], dtype=float)
            return np.array([
                math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
                for i in range(1, len(points))
            ], dtype=float)

        right_vel = velocities(right_wrist)
        left_vel = velocities(left_wrist)
        right_travel = float(np.sum(right_vel))
        left_travel = float(np.sum(left_vel))
        active_side = "right" if right_travel >= left_travel else "left"
        active_vel = right_vel if active_side == "right" else left_vel
        passive_vel = left_vel if active_side == "right" else right_vel
        active_pts = right_wrist if active_side == "right" else left_wrist
        active_shoulders = right_shoulder if active_side == "right" else left_shoulder

        active_avg_vel = float(np.mean(active_vel))
        passive_avg_vel = float(np.mean(passive_vel))
        active_max_vel = float(np.max(active_vel))
        active_travel = max(right_travel, left_travel)
        both_avg_vel = float((active_avg_vel + passive_avg_vel) / 2)

        if len(active_vel) >= 6:
            q = max(2, len(active_vel) // 4)
            approach_decel = float(np.mean(active_vel[:q]) - np.mean(active_vel[-q:]))
            end_variance = float(np.var(active_vel[-q:]))
            start_stillness = float(np.mean(active_vel[:q]))
            end_stillness = float(np.mean(active_vel[-q:]))
        else:
            approach_decel = 0.0
            end_variance = 0.0
            start_stillness = active_avg_vel
            end_stillness = active_avg_vel

        active_disp = 0.0
        if len(active_pts) >= 2:
            active_disp = math.hypot(
                active_pts[-1][0] - active_pts[0][0],
                active_pts[-1][1] - active_pts[0][1],
            )
        path_efficiency = active_disp / max(active_travel, 1e-6)

        active_above_shoulder = False
        if active_pts and active_shoulders:
            active_above_shoulder = active_pts[-1][1] < active_shoulders[-1][1]

        oscillations = _count_direction_reversals(active_pts)
        bilateral_ratio = min(right_travel, left_travel) / max(max(right_travel, left_travel), 1e-6)
        hand_separation_change = 0.0
        if len(wrist_spread) >= 2:
            hand_separation_change = wrist_spread[-1] - wrist_spread[0]

        vis_ratio = (len(right_wrist) + len(left_wrist)) / max(len(frames) * 2, 1)
        stillness_ratio = sum(1 for v in active_vel if v < 0.004) / max(len(active_vel), 1)

        return {
            "active_side": active_side,
            "active_avg_vel": active_avg_vel,
            "active_max_vel": active_max_vel,
            "passive_avg_vel": passive_avg_vel,
            "both_avg_vel": both_avg_vel,
            "approach_decel": approach_decel,
            "end_variance": end_variance,
            "active_travel": active_travel,
            "right_travel": right_travel,
            "left_travel": left_travel,
            "path_efficiency": path_efficiency,
            "active_above_shoulder": active_above_shoulder,
            "trunk_bend": float(np.mean(trunk_angles)) if trunk_angles else 0.0,
            "oscillations": oscillations,
            "bilateral_ratio": bilateral_ratio,
            "hand_separation_change": hand_separation_change,
            "vis_ratio": float(vis_ratio),
            "n_frames": len(frames),
            "stillness_ratio": float(stillness_ratio),
            "start_stillness": start_stillness,
            "end_stillness": end_stillness,
        }

    def _classify(
        self,
        features: dict,
        dur: float,
        prev_label: str | None,
        idx: int,
    ) -> dict:
        expected = self.expected_flow[idx % len(self.expected_flow)] if self.expected_flow else None
        scores = {label: 0.0 for label in _SCORABLE_LABELS}
        evidence = {label: [] for label in _SCORABLE_LABELS}

        av = features["active_avg_vel"]
        mv = features["active_max_vel"]
        pv = features["passive_avg_vel"]
        both = features["both_avg_vel"]
        dec = features["approach_decel"]
        var = features["end_variance"]
        tb = features["trunk_bend"]
        osc = features["oscillations"]
        bilateral = features["bilateral_ratio"]
        still = features["stillness_ratio"]
        path = features["path_efficiency"]
        vis = features["vis_ratio"]

        if both < 0.0045 and still > 0.6:
            delay_label = "UDe" if dur >= 2.0 else "ADe"
            self._add_score(scores, evidence, delay_label, 0.74 + min(0.22, still * 0.22), "both hands still")
            self._add_score(scores, evidence, "H", 0.10, "stationary posture")

        if av < 0.0065 and pv > 0.012:
            contrast = min(1.0, pv / 0.03)
            self._add_score(scores, evidence, "H", 0.56 + contrast * 0.26, "one hand holds while the other works")

        if tb > 18:
            bend_score = min(1.0, (tb - 18) / 20)
            self._add_score(scores, evidence, "B", 0.45 + bend_score * 0.40, "body bend / repositioning")

        if features["active_above_shoulder"] and av < 0.015:
            inspect_score = min(1.0, (0.015 - av) / 0.015)
            self._add_score(scores, evidence, "I", 0.42 + inspect_score * 0.30, "slow motion near head level")

        if osc >= max(3, int(dur * 4)) and av > 0.01:
            use_score = min(1.0, osc / max(4.0, dur * 7))
            self._add_score(scores, evidence, "U", 0.48 + use_score * 0.32, "repetitive oscillating motion")

        if av < 0.018 and dec > 0.0035 and var < 0.00025:
            place_score = (
                min(1.0, (0.018 - av) / 0.018) * 0.30 +
                min(1.0, dec / 0.012) * 0.45 +
                min(1.0, (0.00025 - var) / 0.00025) * 0.25
            )
            self._add_score(scores, evidence, "P", 0.40 + place_score * 0.42, "slow and precise final placement")

        if 0.007 < av < 0.04 and dec > 0.004 and path > 0.35:
            grasp_score = (
                min(1.0, av / 0.03) * 0.25 +
                min(1.0, dec / 0.015) * 0.45 +
                min(1.0, path / 0.9) * 0.30
            )
            self._add_score(scores, evidence, "G", 0.34 + grasp_score * 0.42, "controlled approach before contact")

        if av > 0.02 and dec < -0.0005 and prev_label in _RELEASE_PREV:
            release_score = min(1.0, av / 0.05)
            self._add_score(scores, evidence, "RL", 0.46 + release_score * 0.28, "departure after contact/hold")

        if mv > 0.03:
            transport_score = min(1.0, mv / 0.08) * 0.45 + min(1.0, path / 0.95) * 0.35
            if prev_label in ("G", "H", "U", "P", "RL"):
                self._add_score(scores, evidence, "TL", 0.38 + transport_score * 0.34, "transport after handling/load state")
            self._add_score(scores, evidence, "TE", 0.34 + transport_score * 0.30, "fast transport motion")

        if bilateral > 0.55 and av > 0.009:
            self._add_score(scores, evidence, "TL", 0.12, "both hands move together")
            self._add_score(scores, evidence, "TE", 0.08, "coordinated transfer motion")

        if expected:
            mapped = _normalize_template_label(expected)
            if mapped in scores:
                self._add_score(scores, evidence, mapped, 0.05, f"template prior: {expected}")

        if prev_label == "G":
            self._add_score(scores, evidence, "P", 0.05, "placement often follows grasp")
            self._add_score(scores, evidence, "TL", 0.05, "loaded transport often follows grasp")
        if prev_label in _TRANSPORT_LABELS:
            self._add_score(scores, evidence, "G", 0.04, "grasp often follows transport")

        for label in scores:
            scores[label] *= _visibility_multiplier(vis)

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_label, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        gap = best_score - second_score
        confidence = _clamp(best_score - max(0.0, 0.10 - gap * 0.5), 0.05, 0.98)

        review_reason = ""
        if vis < 0.35:
            review_reason = "visibility too low"
        elif confidence < _REVIEW_THRESHOLD:
            review_reason = "classification ambiguous"
        elif gap < 0.06:
            review_reason = "top candidates too close"

        if not review_reason and best_label in ("ADe", "UDe") and dur < 0.35:
            review_reason = "delay candidate too short"

        if review_reason:
            return {
                "label": "UNKNOWN" if confidence < _REVIEW_THRESHOLD else best_label,
                "confidence": round(confidence, 3),
                "score_gap": gap,
                "scores": _compress_scores(scores),
                "evidence": evidence.get(best_label, []),
                "review_reason": review_reason,
            }

        return {
            "label": best_label,
            "confidence": round(confidence, 3),
            "score_gap": gap,
            "scores": _compress_scores(scores),
            "evidence": evidence.get(best_label, []),
            "review_reason": "",
        }

    def _smooth_labels(self, labels: list[dict]) -> list[dict]:
        if len(labels) < 3:
            return labels

        smoothed = [dict(item) for item in labels]
        for i in range(1, len(smoothed) - 1):
            prev_item = smoothed[i - 1]
            curr_item = smoothed[i]
            next_item = smoothed[i + 1]
            prev_label = prev_item["label"]
            next_label = next_item["label"]

            if prev_label != next_label:
                continue
            if prev_label == "UNKNOWN":
                continue
            if curr_item["confidence"] >= 0.55 and curr_item["label"] != "UNKNOWN":
                continue
            if prev_item["confidence"] < 0.55 or next_item["confidence"] < 0.55:
                continue

            curr_item["label"] = prev_label
            curr_item["label_jp"] = _JP.get(prev_label, prev_label)
            curr_item["is_nva"] = THERBLIGS.get(prev_label, ("", False))[1]
            curr_item["review_required"] = curr_item["confidence"] < _LOW_CONFIDENCE
            reason = curr_item.get("review_reason", "")
            curr_item["review_reason"] = (reason + "; " if reason else "") + "smoothed by neighboring agreement"

        return smoothed

    def _refresh_most_fields(self, labels: list[dict], body_scale: float, features_by_segment: list[dict]) -> None:
        for item, feats in zip(labels, features_by_segment):
            most = self._estimate_most_indices(feats, body_scale, item["label"])
            item["most_A"] = most["A"]
            item["most_B"] = most["B"]
            item["most_G"] = most["G"]
            item["most_P"] = most["P"]
            item["most_tmu"] = most["tmu"]

    @staticmethod
    def _add_score(scores: dict, evidence: dict, label: str, value: float, reason: str) -> None:
        if label not in scores:
            return
        scores[label] += value
        evidence[label].append(reason)

    def _estimate_most_indices(self, features: dict, body_scale: float, therblig: str) -> dict:
        travel_cm = (features["active_travel"] / body_scale * 100) if body_scale > 0 else 0
        A = _a_index(travel_cm)

        tb = features["trunk_bend"]
        B = 6 if tb > 35 else (3 if tb > 15 else 0)

        dec = features["approach_decel"]
        G = 3 if dec > 0.015 else (1 if dec > 0.005 else 0)
        if therblig in ("TE", "TL", "MOVE", "UNKNOWN"):
            G = 0

        var = features["end_variance"]
        if therblig in ("P", "PUT", "POSITION"):
            P = 6 if var < 0.00005 and dec > 0.01 else (3 if dec > 0.004 else 1)
        elif therblig in ("G", "GET"):
            P = 0
        else:
            P = 1 if features["active_avg_vel"] < 0.015 else 0

        tmu = (A + B + G + A + B + P + A) * 10
        return {"A": A, "B": B, "G": G, "P": P, "tmu": tmu}

    @staticmethod
    def _estimate_body_scale(pose_data: list[dict]) -> float:
        heights = []
        for frame in pose_data[: min(100, len(pose_data))]:
            lms = frame.get("landmarks", [])
            if len(lms) < 25:
                continue
            nose = lms[0]
            hip_y = (lms[23]["y"] + lms[24]["y"]) / 2
            if nose["visibility"] > 0.5 and lms[23]["visibility"] > 0.5:
                heights.append(abs(nose["y"] - hip_y))
        if not heights:
            return 0.005
        return float(np.median(heights)) / 102 * 100


def _a_index(travel_cm: float) -> int:
    if travel_cm < 5:
        return 0
    if travel_cm < 30:
        return 1
    if travel_cm < 80:
        return 3
    if travel_cm < 200:
        return 6
    if travel_cm < 500:
        return 10
    return 16


def _empty_features() -> dict:
    return {
        "active_side": "right",
        "active_avg_vel": 0.0,
        "active_max_vel": 0.0,
        "passive_avg_vel": 0.0,
        "both_avg_vel": 0.0,
        "approach_decel": 0.0,
        "end_variance": 0.0,
        "active_travel": 0.0,
        "right_travel": 0.0,
        "left_travel": 0.0,
        "path_efficiency": 0.0,
        "active_above_shoulder": False,
        "trunk_bend": 0.0,
        "oscillations": 0,
        "bilateral_ratio": 0.0,
        "hand_separation_change": 0.0,
        "vis_ratio": 0.0,
        "n_frames": 1,
        "stillness_ratio": 1.0,
        "start_stillness": 0.0,
        "end_stillness": 0.0,
    }


def _normalize_template_label(label: str) -> str:
    mapping = {
        "GET": "G",
        "PUT": "P",
        "MOVE": "TE",
        "WAIT": "ADe",
        "INSPECT": "I",
        "USE_TOOL": "U",
        "POSITION": "P",
    }
    return mapping.get(label, label)


def _count_direction_reversals(points: Iterable[tuple[float, float]]) -> int:
    pts = list(points)
    reversals = 0
    if len(pts) < 5:
        return reversals

    xs = [pt[0] for pt in pts]
    ys = [pt[1] for pt in pts]
    for coords in (xs, ys):
        for i in range(2, len(coords)):
            d1 = coords[i - 1] - coords[i - 2]
            d2 = coords[i] - coords[i - 1]
            if abs(d1) < 1e-5 or abs(d2) < 1e-5:
                continue
            if d1 * d2 < 0:
                reversals += 1
    return reversals


def _visibility_multiplier(vis_ratio: float) -> float:
    return 0.45 + min(0.55, max(0.0, vis_ratio) * 0.55)


def _compress_scores(scores: dict[str, float]) -> dict[str, float]:
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return {label: round(score, 3) for label, score in ranked[:3] if score > 0}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
