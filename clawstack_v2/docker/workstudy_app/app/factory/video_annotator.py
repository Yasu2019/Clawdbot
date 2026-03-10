"""
FactoryVideoAnnotator — Therblig + MOST 分析結果を動画にオーバーレイして書き出す。

各フレームに以下を描画:
  1. 骨格オーバーレイ (手首・肘を強調)
  2. 手首周囲の赤枠 (アプリが着目しているエリア)
  3. 情報パネル (Therbligラベル / MOST A-B-G-P-TMU / 速度 / NVAフラグ)
  4. 下部タイムラインバー (セグメント進捗 + ラベル)
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── Font priority list (IPA Gothic = Japanese support; DejaVu = fallback) ────
_FONT_PATHS = [
    "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

# Skeleton connections to draw (upper-body focus)
_CONNECTIONS = [
    (11, 13), (13, 15),            # right upper arm → wrist
    (12, 14), (14, 16),            # left  upper arm → wrist
    (11, 12),                      # shoulders
    (15, 17), (15, 19), (15, 21),  # right hand rays
    (16, 18), (16, 20), (16, 22),  # left  hand rays
    (11, 23), (12, 24), (23, 24),  # torso
]


def _load_font(size: int) -> ImageFont.ImageFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


class FactoryVideoAnnotator:
    """Renders per-frame annotations onto a factory worker video."""

    def annotate(
        self,
        video_path: str,
        pose_data: list[dict],
        labels: list[dict],
        output_path: str,
        progress_cb=None,
    ) -> str:
        """
        Args:
            video_path:  Path to original video file.
            pose_data:   Per-frame landmarks from PoseEstimator.
            labels:      Therblig segments from TherbligLabeler (with MOST indices).
            output_path: Destination MP4 path.
            progress_cb: Optional (frac, desc) callback.

        Returns: output_path
        """
        cap          = cv2.VideoCapture(video_path)
        fps          = cap.get(cv2.CAP_PROP_FPS) or 30.0
        w            = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h            = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or max(len(pose_data), 1)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out    = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

        # Build frame → label lookup table
        frame_label: dict[int, dict] = {}
        for lbl in labels:
            for fi in range(int(lbl["start_frame"]), int(lbl["end_frame"]) + 1):
                frame_label[fi] = lbl

        font_lg = _load_font(22)
        font_sm = _load_font(15)
        n_labels = len(labels)

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            pose_frame = pose_data[frame_idx] if frame_idx < len(pose_data) else {}
            landmarks  = pose_frame.get("landmarks", [])
            lbl        = frame_label.get(frame_idx)

            # Work on PIL for Japanese text + alpha blending
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(rgb).convert("RGBA")

            overlay = Image.new("RGBA", pil.size, (0, 0, 0, 0))

            self._draw_skeleton(overlay, landmarks, w, h)
            if lbl:
                self._draw_hand_box(overlay, landmarks, w, h, lbl)
                self._draw_info_panel(overlay, lbl, font_lg, font_sm, w, h)

            self._draw_timeline_bar(
                overlay, lbl, frame_idx, total_frames, n_labels, font_sm, w, h
            )

            # Alpha composite and convert back to BGR
            composited = Image.alpha_composite(pil, overlay).convert("RGB")
            bgr = cv2.cvtColor(np.array(composited), cv2.COLOR_RGB2BGR)
            out.write(bgr)

            if progress_cb and frame_idx % 60 == 0:
                progress_cb(
                    frame_idx / total_frames,
                    f"アノテーション動画生成中... {frame_idx}/{total_frames} フレーム",
                )

            frame_idx += 1

        cap.release()
        out.release()
        return output_path

    # ── Drawing helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _draw_skeleton(overlay: Image.Image, landmarks: list[dict], w: int, h: int):
        if not landmarks:
            return
        draw = ImageDraw.Draw(overlay)

        for a_i, b_i in _CONNECTIONS:
            if a_i >= len(landmarks) or b_i >= len(landmarks):
                continue
            a, b = landmarks[a_i], landmarks[b_i]
            if a["visibility"] < 0.35 or b["visibility"] < 0.35:
                continue
            ax, ay = int(a["x"] * w), int(a["y"] * h)
            bx, by = int(b["x"] * w), int(b["y"] * h)
            draw.line([(ax, ay), (bx, by)], fill=(200, 200, 200, 160), width=2)

        for i, lm in enumerate(landmarks):
            if lm["visibility"] < 0.35:
                continue
            x, y = int(lm["x"] * w), int(lm["y"] * h)
            if i in {15, 16}:        # wrists — bright green (main focus)
                r, color = 8, (0, 230, 0, 240)
            elif i in {13, 14}:      # elbows — orange
                r, color = 6, (255, 140, 0, 210)
            elif i in {11, 12}:      # shoulders — sky blue
                r, color = 5, (80, 180, 255, 200)
            else:
                r, color = 4, (200, 200, 200, 140)
            draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=color)

    @staticmethod
    def _draw_hand_box(
        overlay: Image.Image,
        landmarks: list[dict],
        w: int,
        h: int,
        lbl: dict,
    ):
        """Red rectangle around each wrist that is visible."""
        draw    = ImageDraw.Draw(overlay)
        is_nva  = lbl.get("is_nva", False)
        label   = lbl.get("label", "")

        # Colour: bright red for NVA / grasp / position, orange otherwise
        if is_nva or label in ("H", "UDe", "ADe"):
            box_color = (255, 40, 40, 220)
        elif label in ("G", "P", "RL"):
            box_color = (255, 130, 0, 220)
        else:
            box_color = (255, 220, 0, 180)

        box_half = 60 if label in ("G", "P") else 45

        for wrist_idx in (15, 16):   # L=15, R=16
            if wrist_idx >= len(landmarks):
                continue
            lm = landmarks[wrist_idx]
            if lm["visibility"] < 0.4:
                continue
            cx = int(lm["x"] * w)
            cy = int(lm["y"] * h)
            x0, y0 = max(0, cx - box_half), max(0, cy - box_half)
            x1, y1 = min(w, cx + box_half), min(h, cy + box_half)
            for t in range(3):
                draw.rectangle(
                    [(x0 - t, y0 - t), (x1 + t, y1 + t)],
                    outline=box_color,
                )

    @staticmethod
    def _draw_info_panel(
        overlay: Image.Image,
        lbl: dict,
        font_lg: ImageFont.ImageFont,
        font_sm: ImageFont.ImageFont,
        w: int,
        h: int,
    ):
        """Top-left panel: Therblig + MOST + confidence (color-coded)."""
        draw   = ImageDraw.Draw(overlay)
        is_nva = lbl.get("is_nva", False)
        conf   = lbl.get("confidence", 0.0)

        # ── Panel background colour ──────────────────────────────────────────
        # Priority: NVA=red, then confidence tier (green/yellow/orange)
        if is_nva:
            bg = (150, 0, 0, 215)
        elif conf >= 0.75:
            bg = (0, 100, 30, 210)      # dark green  — high confidence
        elif conf >= 0.45:
            bg = (100, 80, 0, 210)      # dark yellow — medium confidence
        else:
            bg = (140, 50, 0, 215)      # dark orange — low confidence

        label_jp = lbl.get("label_jp", lbl.get("label", ""))
        nva_mark = "  ⚠NVA" if is_nva else ""
        A, B, G, P = (lbl.get("most_A", 0), lbl.get("most_B", 0),
                      lbl.get("most_G", 0), lbl.get("most_P", 0))
        tmu    = lbl.get("most_tmu", 0)
        vel    = lbl.get("avg_velocity", 0)
        dur    = lbl.get("duration_sec", 0)
        seg_id = lbl.get("segment_id", 0)
        vis    = lbl.get("vis_ratio", 0.0)

        # Confidence badge text + colour
        if conf >= 0.75:
            conf_tag, conf_color = f" ✓ {conf:.0%}", (100, 255, 120, 255)
        elif conf >= 0.45:
            conf_tag, conf_color = f" △ {conf:.0%}", (255, 230, 80, 255)
        else:
            conf_tag, conf_color = f" ✗ {conf:.0%}", (255, 140, 60, 255)

        lines = [
            (f" {label_jp}{nva_mark}", (255, 255, 255, 255), font_lg),
            (f" A:{A}  B:{B}  G:{G}  P:{P}  → {tmu:.0f} TMU", (210, 210, 210, 255), font_sm),
            (f" vel:{vel:.4f}  dur:{dur:.1f}s  seg:{seg_id}  vis:{vis:.0%}",
             (180, 180, 180, 255), font_sm),
        ]

        panel_w, panel_h = 360, 90
        draw.rectangle([(6, 6), (6 + panel_w, 6 + panel_h)], fill=bg)

        # Confidence badge (top-right corner of panel)
        draw.text((panel_w - 70, 10), conf_tag, fill=conf_color, font=font_sm)

        y_pos = 10
        for text, color, font in lines:
            draw.text((8, y_pos), text, fill=color, font=font)
            y_pos += 27 if font is font_lg else 22

    @staticmethod
    def _draw_timeline_bar(
        overlay: Image.Image,
        lbl: dict | None,
        frame_idx: int,
        total_frames: int,
        n_labels: int,
        font_sm: ImageFont.ImageFont,
        w: int,
        h: int,
    ):
        """Bottom progress bar: global progress + current Therblig."""
        draw  = ImageDraw.Draw(overlay)
        bar_h = 26
        y0    = h - bar_h

        # Dark background strip
        draw.rectangle([(0, y0), (w, h)], fill=(0, 0, 0, 170))

        # Progress fill
        frac   = frame_idx / max(total_frames, 1)
        fill_w = int(w * frac)
        if lbl and lbl.get("is_nva"):
            fill_color = (200, 40, 40, 200)
        else:
            fill_color = (40, 130, 240, 200)

        if fill_w > 0:
            draw.rectangle([(0, y0), (fill_w, h)], fill=fill_color)

        # Segment boundary markers
        if n_labels > 1:
            for i in range(n_labels):
                mark_x = int(w * i / n_labels)
                draw.line([(mark_x, y0), (mark_x, h)], fill=(255, 255, 255, 80), width=1)

        # Text label
        if lbl:
            seg_n  = lbl.get("segment_id", 0) + 1
            label  = lbl.get("label", "")
            lbl_jp = lbl.get("label_jp", "")
            pct    = int(frac * 100)
            txt    = f"  [{label}] {lbl_jp}   Seg {seg_n}/{n_labels}   {pct}%"
        else:
            txt = f"  {int(frac * 100)}%"

        draw.text((4, y0 + 4), txt, fill=(255, 255, 255, 255), font=font_sm)
