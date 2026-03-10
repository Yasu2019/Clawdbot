"""
WorkStudy AI — Main FastAPI + Gradio Application
  • Factory analysis  : Therbligs + MOST (6 processes, MediaPipe pose)
  • Screen analysis   : PC operation recording → click detection → procedure document
      Phase 1: OCR text extraction (procedure_text.txt)
      Phase 2: Excel 手順書 with screenshots + 赤枠 (procedure.xlsx)
"""
import os
import time
import uuid
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import yaml
import gradio as gr
from fastapi import FastAPI

from pose.estimator import PoseEstimator
from analysis.segmenter import AutoSegmenter
from analysis.labeler import TherbligLabeler
from analysis.metrics import MetricsEngine
from report.generator import ReportGenerator
from screen.cursor_tracker import CursorTracker
from screen.annotator import ScreenAnnotator
from screen.procedure_writer import ProcedureWriter
from factory.procedure_writer import FactoryProcedureWriter
from factory.video_annotator import FactoryVideoAnnotator

PROJECTS_DIR = Path(os.getenv("WORKSTUDY_PROJECTS", "/work/projects"))
CONFIG_DIR   = Path(__file__).parent / "config"

app = FastAPI(title="WorkStudy AI", version="0.2.0")


def load_templates():
    path = CONFIG_DIR / "templates.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["templates"]

TEMPLATES       = load_templates()
TEMPLATE_CHOICES = {v["label"]: k for k, v in TEMPLATES.items()}


# ── Progress helper (with real-time ETA) ────────────────────────────────────

def _make_timed_cb(
    progress,
    p_start: float,
    p_end: float,
    overall_start: float,
):
    """
    Returns a progress callback that:
      1. Maps local fraction [0, 1] → global range [p_start, p_end]
      2. Appends live ETA and estimated completion time to every desc string

    Args:
        progress:       Gradio gr.Progress() object.
        p_start/p_end:  Slice of the master bar this step occupies.
        overall_start:  time.monotonic() captured when the whole job started.
    """
    def _cb(frac: float, desc: str = ""):
        global_frac   = p_start + frac * (p_end - p_start)
        elapsed       = time.monotonic() - overall_start

        # ETA: needs at least 3 % global progress and 2 s elapsed for stability
        if global_frac > 0.03 and elapsed > 2.0:
            projected_total = elapsed / global_frac          # seconds for 100 %
            remain_sec      = max(0.0, projected_total - elapsed)
            finish_dt       = datetime.now() + timedelta(seconds=remain_sec)

            if remain_sec >= 3600:
                h, m = divmod(int(remain_sec) // 60, 60)
                remain_str = f"{h}時間{m:02d}分"
            elif remain_sec >= 60:
                m, s = divmod(int(remain_sec), 60)
                remain_str = f"{m}分{s:02d}秒"
            else:
                remain_str = f"{int(remain_sec)}秒"

            eta_suffix = (
                f"  ⏱ 残り約{remain_str}"
                f"  完了予定 {finish_dt.strftime('%H:%M:%S')}"
            )
        elif global_frac > 0.01:
            eta_suffix = "  ⏱ 完了予定 計算中..."
        else:
            eta_suffix = ""

        progress(global_frac, desc=(desc + eta_suffix) if desc else eta_suffix)

    return _cb


# ── Screen analysis pipeline ────────────────────────────────────────────────

def run_screen_analysis(video_file, template, project_id, project_dir, video_path, progress):
    """
    PC操作動画の全解析パイプライン:
      1. カーソル追跡・クリック検出
      2. アノテーション動画生成（赤リング + "クリック"ラベル）
      3. Phase 1: OCRテキスト抽出 → procedure_text.txt
      4. Phase 2: Excel手順書生成 → procedure.xlsx (スクリーンショット + 赤枠)
      5. KPI算出 + KPIレポートPDF
    """
    overall_start = time.monotonic()

    # ── Step 1: クリック検出  (progress 0.05 → 0.28) ───────────────────────
    progress(0.05, desc="カーソル追跡・クリック検出 開始...")
    tracker = CursorTracker()
    result  = tracker.analyze_video(
        str(video_path),
        progress_cb=_make_timed_cb(progress, 0.05, 0.28, overall_start),
    )
    events  = result["events"]

    with open(project_dir / "click_events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    # ── Step 2: アノテーション動画  (progress 0.28 → 0.50) ─────────────────
    progress(0.28, desc="アノテーション動画生成 開始...")
    annotated_path = str(project_dir / "annotated.mp4")
    ScreenAnnotator().annotate(
        str(video_path), events, annotated_path,
        progress_cb=_make_timed_cb(progress, 0.28, 0.50, overall_start),
    )

    # ── Step 3 (Phase 1): OCRテキスト抽出  (progress 0.50 → 0.65) ──────────
    progress(0.50, desc="Phase 1: 画面テキスト抽出 (OCR) 開始...")
    writer   = ProcedureWriter()
    txt_path = writer.write_text_log(
        events, str(video_path), project_dir,
        title=f"PC操作 作業手順書 — {template['label']}",
        progress_cb=_make_timed_cb(progress, 0.50, 0.65, overall_start),
    )

    # ── Step 4 (Phase 2): Excel手順書生成  (progress 0.65 → 0.88) ──────────
    progress(0.65, desc="Phase 2: Excel手順書生成 (スクリーンショット + 赤枠) 開始...")
    proc_xlsx = writer.write_excel(
        events, str(video_path), project_dir,
        title=f"PC操作 作業手順書 — {template['label']}",
        progress_cb=_make_timed_cb(progress, 0.65, 0.88, overall_start),
    )

    # ── Step 5: KPI + KPIレポートPDF  (progress 0.88 → 1.0) ────────────────
    elapsed_total = time.monotonic() - overall_start
    m, s = divmod(int(elapsed_total), 60)
    progress(0.88, desc=f"KPI算出・KPIレポート生成中...  (総経過時間 {m}分{s:02d}秒)")
    metrics_raw = CursorTracker.compute_metrics(
        events, result["fps"], result["total_frames"]
    )
    metrics = {"kpi": metrics_raw, "waste_fired": [], "ergo": {}}
    _check_screen_waste(metrics, template)

    with open(project_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    # Build pseudo-labels for PDF timeline
    fake_labels = [
        {
            "segment_id":  i,
            "start_frame": ev["frame"],
            "end_frame":   ev["frame"],
            "start_sec":   ev["time_sec"],
            "end_sec":     ev["time_sec"],
            "label":       ev["type"].upper(),
            "label_jp":    "ダブルクリック" if ev["type"] == "dblclick" else "クリック",
            "duration_sec": 0.0,
            "avg_velocity": 0.0,
            "is_nva":      False,
        }
        for i, ev in enumerate(events)
    ]
    reporter  = ReportGenerator(template)
    pdf_path  = reporter.generate_pdf(metrics, fake_labels, project_dir)

    progress(1.0, desc="完了")

    # ── サマリ ───────────────────────────────────────────────────────────────
    kpi = metrics_raw
    from screen.ocr_extractor import OCRExtractor
    ocr_status = "✅ 有効 (Tesseract)" if OCRExtractor.is_available() else "⚠️ 無効 (Tesseract未インストール)"

    summary_lines = [
        f"✅ PC操作解析完了  ID: {project_id}",
        f"テンプレート  : {template['label']}",
        f"録画時間      : {kpi.get('total_duration_sec', 0):.1f} 秒",
        f"OCRエンジン   : {ocr_status}",
        "",
        "🖱 クリック統計:",
        f"  • 総クリック数    : {kpi.get('total_clicks', 0)} 回",
        f"  • ダブルクリック  : {kpi.get('double_clicks', 0)} 回",
        f"  • クリック / 分   : {kpi.get('clicks_per_min', 0):.1f}",
        f"  • 平均間隔        : {kpi.get('avg_interval_sec', 0):.2f} 秒",
        f"  • アイドル比率    : {kpi.get('idle_ratio', 0):.1%}",
        f"  • 操作ゾーン数    : {kpi.get('unique_zones', 0)}",
        "",
        "📄 出力ファイル:",
        f"  • procedure_text.txt — OCRテキスト手順ログ (Phase 1)",
        f"  • procedure.xlsx     — 画像付き赤枠手順書 (Phase 2)",
        f"  • annotated.mp4      — クリック可視化動画",
        f"  • report.pdf         — KPIレポート",
    ]
    waste_fired = metrics.get("waste_fired", [])
    if waste_fired:
        summary_lines += ["", "⚠️ 発火した無駄パターン:"]
        for w in waste_fired:
            summary_lines.append(f"  🔴 {w['description']}")
            summary_lines.append(f"     → {w['suggestion']}")
    else:
        summary_lines += ["", "✅ 無駄パターンの発火なし"]

    # Click timeline for display (first 25 events)
    timeline_md = "| # | 時刻 | X | Y | 種別 |\n|---|------|---|---|------|\n"
    for i, ev in enumerate(events[:25]):
        mm, ss = divmod(int(ev["time_sec"]), 60)
        kind   = "ダブル" if ev["type"] == "dblclick" else "クリック"
        timeline_md += f"| {i+1} | {mm:02d}:{ss:02d} | {ev['x']} | {ev['y']} | {kind} |\n"
    if len(events) > 25:
        timeline_md += f"\n*… 他 {len(events) - 25} 件*"

    return (
        "\n".join(summary_lines),
        timeline_md,
        str(pdf_path),
        str(proc_xlsx),    # procedure.xlsx as "Excel出力"
        str(txt_path),     # procedure_text.txt as "テキストログ"
        str(project_dir),
        annotated_path,
    )


def _check_screen_waste(metrics: dict, template: dict):
    kpi = metrics["kpi"]
    for wp in template.get("waste_patterns", []):
        t      = wp["trigger"]
        actual = kpi.get(t["metric"])
        if actual is None:
            continue
        fired = (t["op"] == ">" and actual > t["value"]) or \
                (t["op"] == "<" and actual < t["value"])
        if fired:
            metrics["waste_fired"].append({
                "id":           wp["id"],
                "description":  wp["description"],
                "metric":       t["metric"],
                "actual_value": actual,
                "threshold":    t["value"],
                "suggestion":   wp["suggestion"],
            })


# ── Factory (body pose) analysis pipeline ──────────────────────────────────

def run_factory_analysis(video_file, template, project_id, project_dir, video_path, progress):
    """既存の工場動作分析パイプライン（MediaPipe骨格推定）。"""
    overall_start = time.monotonic()

    def _factory_progress(frac: float, desc: str):
        """Manual progress call with ETA appended."""
        elapsed = time.monotonic() - overall_start
        if frac > 0.05 and elapsed > 2.0:
            projected  = elapsed / frac
            remain_sec = max(0.0, projected - elapsed)
            finish_dt  = datetime.now() + timedelta(seconds=remain_sec)
            if remain_sec >= 60:
                m, s = divmod(int(remain_sec), 60)
                remain_str = f"{m}分{s:02d}秒"
            else:
                remain_str = f"{int(remain_sec)}秒"
            desc += f"  ⏱ 残り約{remain_str}  完了予定 {finish_dt.strftime('%H:%M:%S')}"
        progress(frac, desc=desc)

    _factory_progress(0.1, "骨格推定中...")
    estimator = PoseEstimator()
    pose_data = estimator.process(str(video_path))
    with open(project_dir / "pose.jsonl", "w") as f:
        for frame in pose_data:
            f.write(json.dumps(frame, ensure_ascii=False) + "\n")

    _factory_progress(0.3, "自動セグメント分割中...")
    segmenter = AutoSegmenter()
    segments  = segmenter.segment(pose_data)
    with open(project_dir / "segments.json", "w") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    _factory_progress(0.5, "サーブリッグ分類中...")
    labeler = TherbligLabeler(template)
    labels  = labeler.label(segments, pose_data)
    with open(project_dir / "labels.json", "w") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)

    _factory_progress(0.65, "KPI算出中...")
    engine  = MetricsEngine(template)
    metrics = engine.compute(pose_data, segments, labels)
    with open(project_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    _factory_progress(0.68, "KPIレポート生成中...")
    reporter = ReportGenerator(template)
    pdf_path = reporter.generate_pdf(metrics, labels, project_dir)

    _factory_progress(0.72, "作業標準書Excel生成中（骨格オーバーレイ付きスクリーンショット）...")
    factory_writer = FactoryProcedureWriter()
    proc_xlsx = factory_writer.write_excel(
        labels, pose_data, str(video_path), project_dir, template,
        title=f"作業標準書 — {template['label']}",
        progress_cb=_make_timed_cb(progress, 0.72, 0.86, overall_start),
    )

    # ── アノテーション動画生成 (0.86 → 0.99) ─────────────────────────────────
    _factory_progress(0.86, "アノテーション動画生成中（赤枠 + Therbligラベル + MOSTオーバーレイ）...")
    annotated_path = str(project_dir / "annotated.mp4")
    try:
        FactoryVideoAnnotator().annotate(
            str(video_path),
            pose_data,
            labels,
            annotated_path,
            progress_cb=_make_timed_cb(progress, 0.86, 0.99, overall_start),
        )
    except Exception as e:
        annotated_path = None
        _factory_progress(0.99, f"⚠ アノテーション動画生成失敗 ({e})")

    elapsed_total = time.monotonic() - overall_start
    m_tot, s_tot = divmod(int(elapsed_total), 60)
    progress(1.0, desc=f"完了  (総処理時間: {m_tot}分{s_tot:02d}秒)")

    summary_lines = [
        f"✅ 解析完了  ID: {project_id}",
        f"テンプレート: {template['label']}",
        f"総処理時間  : {m_tot}分{s_tot:02d}秒",
        "",
        "📊 主要KPI:",
    ]
    for kpi_name in template["focus_kpi"][:5]:
        val = metrics.get("kpi", {}).get(kpi_name, "N/A")
        if isinstance(val, float):
            val = f"{val:.2f}"
        summary_lines.append(f"  • {kpi_name}: {val}")

    waste_fired = metrics.get("waste_fired", [])
    summary_lines.append("")
    if waste_fired:
        summary_lines.append("⚠️ 発火した無駄パターン:")
        for w in waste_fired[:3]:
            summary_lines.append(f"  🔴 {w['description']}")
            summary_lines.append(f"     → {w['suggestion']}")
    else:
        summary_lines.append("✅ 無駄パターンの発火なし")

    ergo = metrics.get("ergo", {})
    if ergo:
        summary_lines += [
            "", "🦴 姿勢負荷:",
            f"  • 腰屈曲リスク率: {ergo.get('trunk_risk_ratio', 0):.1%}",
            f"  • 肩挙上リスク率: {ergo.get('shoulder_risk_ratio', 0):.1%}",
        ]

    kpi_data = metrics.get("kpi", {})
    avg_conf  = kpi_data.get("avg_confidence", 0.0)
    low_ratio = kpi_data.get("low_confidence_ratio", 0.0)
    hi_ratio  = kpi_data.get("high_confidence_ratio", 0.0)
    if avg_conf > 0:
        if avg_conf >= 0.75:
            conf_icon = "✅"
        elif avg_conf >= 0.45:
            conf_icon = "⚠️"
        else:
            conf_icon = "❌"
        summary_lines += [
            "", f"{conf_icon} 判定信頼度:",
            f"  • 平均信頼度      : {avg_conf:.1%}",
            f"  • 高信頼 (≥75%)  : {hi_ratio:.1%}",
            f"  • 低信頼 (<45%)  : {low_ratio:.1%}",
        ]
        if low_ratio > 0.3:
            summary_lines.append(
                "  ⚠ 低信頼セグメントが多い → 照明改善・カメラ正面設置を推奨"
            )

    timeline_md = "| # | 開始(s) | 終了(s) | ラベル | 時間(s) |\n|---|---------|---------|--------|--------|\n"
    for i, lbl in enumerate(labels[:20]):
        dur = lbl["end_sec"] - lbl["start_sec"]
        timeline_md += (
            f"| {i+1} | {lbl['start_sec']:.1f} | {lbl['end_sec']:.1f} "
            f"| {lbl['label']} | {dur:.1f} |\n"
        )

    return (
        "\n".join(summary_lines),
        timeline_md,
        str(pdf_path),
        str(proc_xlsx),
        None,              # no text log for factory mode
        str(project_dir),
        annotated_path,    # annotated MP4 with Therblig + MOST overlay
    )


# ── Dispatcher ──────────────────────────────────────────────────────────────

def run_analysis(video_file, template_label, progress=gr.Progress()):
    """Route to factory or screen pipeline depending on template."""
    if video_file is None:
        return "⚠️ 動画をアップロードしてください", None, None, None, None, None, None

    template_key = TEMPLATE_CHOICES.get(template_label)
    if not template_key:
        return "⚠️ テンプレートを選択してください", None, None, None, None, None, None

    template    = TEMPLATES[template_key]
    project_id  = str(uuid.uuid4())[:8]
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    video_path = project_dir / "input.mp4"
    shutil.copy2(video_file, video_path)

    if template.get("_mode") == "screen":
        return run_screen_analysis(
            video_file, template, project_id, project_dir, video_path, progress
        )
    else:
        return run_factory_analysis(
            video_file, template, project_id, project_dir, video_path, progress
        )


# ── Gradio UI ───────────────────────────────────────────────────────────────

with gr.Blocks(
    title="WorkStudy AI — Therbligs + MOST",
    theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
    css="""
    .main-header { text-align: center; margin-bottom: 20px; }
    .main-header h1 { color: #2563eb; font-size: 28px; }
    .main-header p  { color: #64748b; }
    .output-files   { background: #f8faff; border-radius: 8px; padding: 8px; }
    """
) as demo:
    gr.HTML("""
    <div class="main-header">
        <h1>🏭 WorkStudy AI</h1>
        <p>Therbligs + MOST 動作分析 / PC操作画面録画 → 自動手順書生成</p>
    </div>
    """)

    with gr.Row():
        # ── Left panel ────────────────────────────────────────────────────
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ 設定")
            video_input = gr.Video(label="動画アップロード (MP4 / 最大2GB)")
            gr.Markdown(
                "**テンプレート選択ガイド**\n"
                "- 🏭 工場作業者の動作動画 → 工場テンプレート（プレス・検査・成形など）\n"
                "- 🖥 PCデスクトップ操作動画 → **PC操作 画面録画分析**"
            )
            template_select = gr.Dropdown(
                choices=list(TEMPLATE_CHOICES.keys()),
                label="工程テンプレート",
                value=list(TEMPLATE_CHOICES.keys())[0] if TEMPLATE_CHOICES else None,
            )
            run_btn = gr.Button("▶ 解析実行", variant="primary", size="lg")

            with gr.Group(elem_classes="output-files"):
                gr.Markdown("### 📁 出力ファイル")
                pdf_output   = gr.File(label="KPI レポート PDF")
                xlsx_output  = gr.File(
                    label="作業標準書 Excel\n"
                          "🏭工場: 骨格付きスクリーンショット＋動作ラベル\n"
                          "🖥PC: クリック赤枠＋OCRテキスト"
                )
                txt_output   = gr.File(label="OCRテキストログ (PC操作モード Phase 1)")
                project_path = gr.Textbox(label="プロジェクトフォルダ", interactive=False)

        # ── Right panel ───────────────────────────────────────────────────
        with gr.Column(scale=2):
            gr.Markdown("### 📊 解析結果")
            result_summary = gr.Textbox(
                label="KPI サマリ & 改善提案",
                lines=20,
                interactive=False,
            )
            gr.Markdown("### ⏱ タイムライン / クリックログ (先頭25件)")
            timeline_display = gr.Markdown(
                value="*解析を実行すると、セグメント別タイムラインが表示されます*"
            )
            gr.Markdown("### 🎬 アノテーション動画")
            annotated_video = gr.Video(
                label="🏭 工場モード: 赤枠(手首) + Therbligラベル + MOSTインデックス\n"
                      "🖥 PCモード: クリック赤リング + 'クリック'ラベル",
                interactive=False,
            )

    run_btn.click(
        fn=run_analysis,
        inputs=[video_input, template_select],
        outputs=[
            result_summary,
            timeline_display,
            pdf_output,
            xlsx_output,
            txt_output,
            project_path,
            annotated_video,
        ],
    )

app = gr.mount_gradio_app(app, demo, path="/", max_file_size=2 * 1024 * 1024 * 1024)  # 2GB
