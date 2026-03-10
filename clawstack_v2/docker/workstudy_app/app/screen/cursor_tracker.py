"""
CursorTracker — Detects cursor position and click events in a screen recording.

Strategy:
  1. MOG2 background subtractor (history=5) to isolate moving objects (cursor)
  2. Track the smallest / most compact moving blob as the cursor candidate
  3. Click = cursor velocity drops near zero for DWELL_FRAMES + significant UI
     frame change detected at that position (button highlight, dropdown open, etc.)
  4. Double-click = two clicks within 0.4 s at the same location
"""
import cv2
import numpy as np
from collections import deque


class CursorTracker:
    DWELL_FRAMES = 4           # frames cursor stays still to confirm dwell
    VELOCITY_THRESHOLD = 12    # max std-dev (px) over dwell window = "stopped"
    UI_CHANGE_PIXELS = 250     # changed pixels to confirm UI reacted to click
    MIN_CLICK_INTERVAL = 0.25  # minimum seconds between registered clicks
    DOUBLE_CLICK_WINDOW = 0.40 # max seconds between two clicks = double-click
    CURSOR_BLOB_MIN = 8        # min blob area (px²)
    CURSOR_BLOB_MAX = 2000     # max blob area — filters out large moving panels

    def analyze_video(
        self,
        video_path: str,
        sample_every: int = 1,
        progress_cb=None,
    ) -> dict:
        """
        Analyze a screen recording for cursor movements and click events.

        Args:
            video_path:   Path to the screen recording file.
            sample_every: Analyse every Nth frame (1 = all frames).
            progress_cb:  Optional callable(fraction: float, desc: str) for
                          real-time progress reporting.  fraction ∈ [0, 1].

        Returns:
            {
                "events":       list of click-event dicts,
                "fps":          float,
                "total_frames": int,
                "width":        int,
                "height":       int,
            }
        """
        cap = cv2.VideoCapture(video_path)
        fps          = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Short-history MOG2: treats recent past as background → cursor pops out
        fgbg = cv2.createBackgroundSubtractorMOG2(
            history=5, varThreshold=40, detectShadows=False
        )

        pos_history: deque = deque(maxlen=self.DWELL_FRAMES + 3)
        events: list[dict] = []
        prev_gray = None
        frame_idx = 0
        last_click_sec = -self.MIN_CLICK_INTERVAL * 2

        _PROGRESS_INTERVAL = 90  # call progress_cb every N frames

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # ── Real-time progress update ─────────────────────────────────
            if progress_cb and total_frames > 0 and frame_idx % _PROGRESS_INTERVAL == 0:
                elapsed   = frame_idx / fps
                frac      = frame_idx / total_frames
                clicks_n  = len(events)
                mm, ss    = divmod(int(elapsed), 60)
                progress_cb(
                    frac,
                    f"カーソル追跡 {mm:02d}:{ss:02d} / "
                    f"{int(total_frames/fps)//60:02d}:{int(total_frames/fps)%60:02d}  "
                    f"クリック検出: {clicks_n} 件",
                )

            if frame_idx % sample_every == 0:
                gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                fg_mask = fgbg.apply(frame)

                # ── Cursor position ──────────────────────────────────────────
                contours, _ = cv2.findContours(
                    fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                cursor_pos = None
                best_score = -1.0
                for c in contours:
                    area = cv2.contourArea(c)
                    if not (self.CURSOR_BLOB_MIN < area < self.CURSOR_BLOB_MAX):
                        continue
                    M = cv2.moments(c)
                    if M["m00"] == 0:
                        continue
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    perim = cv2.arcLength(c, True)
                    compactness = 4 * np.pi * area / (perim ** 2 + 1e-8)
                    # Prefer compact (round/arrow-like) and small blobs
                    score = compactness + 1.0 / (area + 1)
                    if score > best_score:
                        best_score = score
                        cursor_pos = (cx, cy)

                # ── Frame-difference for UI change detection ─────────────────
                diff_pixels = 0
                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray)
                    _, diff_bin = cv2.threshold(diff, 20, 1, cv2.THRESH_BINARY)
                    diff_pixels = int(diff_bin.sum())

                pos_history.append({
                    "frame":      frame_idx,
                    "pos":        cursor_pos,
                    "diff_pixels": diff_pixels,
                })

                # ── Click detection ───────────────────────────────────────────
                if len(pos_history) >= self.DWELL_FRAMES + 1:
                    window = list(pos_history)[-self.DWELL_FRAMES:]
                    valid  = [h["pos"] for h in window if h["pos"] is not None]

                    if len(valid) >= self.DWELL_FRAMES - 1:
                        xs = [p[0] for p in valid]
                        ys = [p[1] for p in valid]
                        velocity = float(np.std(xs) + np.std(ys))
                        current_diff = pos_history[-1]["diff_pixels"]
                        current_sec  = frame_idx / fps

                        if (
                            velocity < self.VELOCITY_THRESHOLD
                            and current_diff > self.UI_CHANGE_PIXELS
                            and current_sec - last_click_sec > self.MIN_CLICK_INTERVAL
                        ):
                            avg_x = int(np.mean(xs))
                            avg_y = int(np.mean(ys))

                            # Double-click check
                            ev_type = "click"
                            if events:
                                prev = events[-1]
                                dt = current_sec - prev["time_sec"]
                                dist = abs(prev["x"] - avg_x) + abs(prev["y"] - avg_y)
                                if dt < self.DOUBLE_CLICK_WINDOW and dist < 30:
                                    ev_type = "dblclick"
                                    events[-1]["type"] = "dblclick"  # upgrade previous

                            events.append({
                                "frame":      frame_idx,
                                "time_sec":   round(current_sec, 3),
                                "x":          avg_x,
                                "y":          avg_y,
                                "type":       ev_type,
                                "diff_pixels": current_diff,
                            })
                            last_click_sec = current_sec

                prev_gray = gray

            frame_idx += 1

        cap.release()
        return {
            "events":       events,
            "fps":          fps,
            "total_frames": total_frames,
            "width":        width,
            "height":       height,
        }

    @staticmethod
    def compute_metrics(events: list[dict], fps: float, total_frames: int) -> dict:
        """Derive KPI metrics from detected click events."""
        total_sec = total_frames / fps if fps > 0 else 1
        clicks    = [e for e in events if e["type"] in ("click", "dblclick")]
        dblclicks = [e for e in events if e["type"] == "dblclick"]

        # Inter-click intervals
        intervals = []
        for i in range(1, len(clicks)):
            intervals.append(clicks[i]["time_sec"] - clicks[i - 1]["time_sec"])

        # Idle periods (gap > 5 s with no click)
        idle_periods = [iv for iv in intervals if iv > 5.0]

        # Spatial clustering: how many unique screen zones (quadrant of 200px grid)
        zone_set = set()
        for e in clicks:
            zone_set.add((e["x"] // 200, e["y"] // 200))

        return {
            "total_clicks":       len(clicks),
            "double_clicks":      len(dblclicks),
            "clicks_per_min":     round(len(clicks) / (total_sec / 60), 2),
            "avg_interval_sec":   round(float(np.mean(intervals)), 2) if intervals else 0.0,
            "idle_periods":       len(idle_periods),
            "idle_total_sec":     round(sum(idle_periods), 1),
            "idle_ratio":         round(sum(idle_periods) / total_sec, 3),
            "unique_zones":       len(zone_set),
            "total_duration_sec": round(total_sec, 1),
        }
