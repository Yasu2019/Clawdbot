"""
ScreenAnnotator — Overlays click markers, labels, and a click-counter HUD
onto a screen recording using OpenCV.

Visual design:
  - Click  : expanding red ring + 赤枠 "クリック" label (fades over 0.5 s)
  - DblClick: expanding orange ring + "ダブルクリック" label
  - Crosshair at exact click position
  - Top-left HUD: cumulative click count + elapsed time
"""
import cv2
import numpy as np
from pathlib import Path


# BGR colour palette
_RED    = (30,  30, 210)
_ORANGE = (20, 150, 240)
_WHITE  = (255, 255, 255)
_DARK   = (20,  20,  20)

_FONT = cv2.FONT_HERSHEY_SIMPLEX


class ScreenAnnotator:
    RIPPLE_SEC   = 0.55   # seconds the ripple animation lasts
    LABEL_SHOW   = 0.35   # first N seconds of ripple: show text label

    def annotate(
        self,
        video_path: str,
        events: list[dict],
        output_path: str,
        codec: str = "mp4v",
        progress_cb=None,
    ) -> str:
        """
        Write annotated video with click overlays to *output_path*.

        Args:
            video_path:  Original screen recording.
            events:      List of click-event dicts from CursorTracker.
            output_path: Destination file path (mp4).
            codec:       FourCC codec string (default 'mp4v').

        Returns:
            output_path on success.
        """
        cap          = cv2.VideoCapture(video_path)
        fps          = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w            = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h            = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out    = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

        _PROGRESS_INTERVAL = 150  # update every N frames

        ripple_frames = max(1, int(fps * self.RIPPLE_SEC))
        label_frames  = max(1, int(fps * self.LABEL_SHOW))

        # Build lookup: frame_idx → (event, offset_within_ripple)
        frame_events: dict[int, tuple] = {}
        for ev in events:
            for off in range(ripple_frames):
                fi = ev["frame"] + off
                if fi not in frame_events:          # earlier event wins
                    frame_events[fi] = (ev, off)

        frame_idx  = 0
        click_seen = 0  # running count for HUD

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # ── Real-time progress ────────────────────────────────────────
            if progress_cb and total_frames > 0 and frame_idx % _PROGRESS_INTERVAL == 0:
                frac   = frame_idx / total_frames
                pct    = int(frac * 100)
                mm, ss = divmod(int(frame_idx / fps), 60)
                progress_cb(frac, f"動画アノテーション {pct}%  ({mm:02d}:{ss:02d})")

            # Update running click count
            click_seen = sum(1 for e in events if e["frame"] <= frame_idx)

            # ── Ripple overlay ────────────────────────────────────────────────
            if frame_idx in frame_events:
                ev, off = frame_events[frame_idx]
                x, y   = ev["x"], ev["y"]
                is_dbl = ev.get("type") == "dblclick"
                color  = _ORANGE if is_dbl else _RED

                # Fade alpha: 1.0 → 0.0 over ripple_frames
                alpha = max(0.0, 1.0 - off / ripple_frames)

                # Expanding ring radius
                r_outer = 16 + off * 4
                r_inner = max(4, r_outer - 12)

                # Draw rings onto a temporary overlay then blend
                overlay = frame.copy()
                cv2.circle(overlay, (x, y), r_outer, color, 2)
                cv2.circle(overlay, (x, y), r_inner, color, 1)

                # Inner solid dot at frame-0 only
                if off == 0:
                    cv2.circle(overlay, (x, y), 5, color, -1)

                # Red bounding box (枠) around the click zone
                margin = r_outer + 4
                pt1 = (max(0, x - margin), max(0, y - margin))
                pt2 = (min(w - 1, x + margin), min(h - 1, y + margin))
                cv2.rectangle(overlay, pt1, pt2, color, 2)

                cv2.addWeighted(overlay, alpha, frame, 1.0 - alpha, 0, frame)

                # Crosshair at exact click position (always visible during ripple)
                cv2.drawMarker(frame, (x, y), color, cv2.MARKER_CROSS, 14, 2, cv2.LINE_AA)

                # ── Text label (shown only during first LABEL_SHOW seconds) ─
                if off < label_frames:
                    label = "ダブルクリック" if is_dbl else "クリック"
                    scale, thick = 0.6, 1
                    (tw, th), bl = cv2.getTextSize(label, _FONT, scale, thick)
                    tx = max(2, x - tw // 2)
                    ty = max(th + 6, y - r_outer - 8)

                    # Background box with border
                    pad = 4
                    cv2.rectangle(
                        frame,
                        (tx - pad, ty - th - pad),
                        (tx + tw + pad, ty + pad),
                        color, -1,
                    )
                    cv2.rectangle(
                        frame,
                        (tx - pad, ty - th - pad),
                        (tx + tw + pad, ty + pad),
                        _WHITE, 1,
                    )
                    cv2.putText(
                        frame, label, (tx, ty),
                        _FONT, scale, _WHITE, thick, cv2.LINE_AA,
                    )

            # ── HUD (top-left corner) ─────────────────────────────────────────
            elapsed = frame_idx / fps
            hud_lines = [
                f"CLICK: {click_seen}",
                f"TIME : {elapsed:.1f}s",
            ]
            for li, text in enumerate(hud_lines):
                hy = 28 + li * 24
                # Shadow
                cv2.putText(frame, text, (11, hy + 1), _FONT, 0.65, _DARK,  2, cv2.LINE_AA)
                cv2.putText(frame, text, (10, hy),     _FONT, 0.65, _WHITE, 1, cv2.LINE_AA)

            out.write(frame)
            frame_idx += 1

        cap.release()
        out.release()
        return output_path
