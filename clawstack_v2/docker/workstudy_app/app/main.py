"""
WorkStudy AI — Main FastAPI + Gradio Application
Therbligs + MOST compatible motion analysis for 6 factory processes.
"""
import os
import uuid
import json
import shutil
from pathlib import Path
from typing import Optional

import yaml
import gradio as gr
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from pose.estimator import PoseEstimator
from analysis.segmenter import AutoSegmenter
from analysis.labeler import TherbligLabeler
from analysis.metrics import MetricsEngine
from report.generator import ReportGenerator

PROJECTS_DIR = Path(os.getenv("WORKSTUDY_PROJECTS", "/work/projects"))
CONFIG_DIR = Path(__file__).parent / "config"

app = FastAPI(title="WorkStudy AI", version="0.1.0")


def load_templates():
    path = CONFIG_DIR / "templates.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["templates"]

TEMPLATES = load_templates()
TEMPLATE_CHOICES = {v["label"]: k for k, v in TEMPLATES.items()}


def run_analysis(video_file, template_label, progress=gr.Progress()):
    """Full pipeline: Upload → Pose → Segment → Label → Metrics → Report"""
    if video_file is None:
        return "⚠️ 動画をアップロードしてください", None, None, None, None

    template_key = TEMPLATE_CHOICES.get(template_label)
    if not template_key:
        return "⚠️ テンプレートを選択してください", None, None, None, None

    template = TEMPLATES[template_key]
    project_id = str(uuid.uuid4())[:8]
    project_dir = PROJECTS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    # Copy video
    video_path = project_dir / "input.mp4"
    shutil.copy2(video_file, video_path)

    progress(0.1, desc="骨格推定中...")
    estimator = PoseEstimator()
    pose_data = estimator.process(str(video_path))
    with open(project_dir / "pose.jsonl", "w") as f:
        for frame in pose_data:
            f.write(json.dumps(frame, ensure_ascii=False) + "\n")

    progress(0.3, desc="自動セグメント分割中...")
    segmenter = AutoSegmenter()
    segments = segmenter.segment(pose_data)
    with open(project_dir / "segments.json", "w") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)

    progress(0.5, desc="サーブリッグ分類中...")
    labeler = TherbligLabeler(template)
    labels = labeler.label(segments, pose_data)
    with open(project_dir / "labels.json", "w") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)

    progress(0.7, desc="KPI算出中...")
    engine = MetricsEngine(template)
    metrics = engine.compute(pose_data, segments, labels)
    with open(project_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    progress(0.85, desc="レポート生成中...")
    reporter = ReportGenerator(template)
    pdf_path = reporter.generate_pdf(metrics, labels, project_dir)
    xlsx_path = reporter.generate_xlsx(metrics, labels, project_dir)

    progress(1.0, desc="完了")

    # Build summary
    summary_lines = [f"✅ 解析完了 (ID: {project_id})", f"テンプレート: {template['label']}", ""]
    summary_lines.append("📊 主要KPI:")
    for kpi_name in template["focus_kpi"][:5]:
        val = metrics.get("kpi", {}).get(kpi_name, "N/A")
        if isinstance(val, float):
            val = f"{val:.2f}"
        summary_lines.append(f"  • {kpi_name}: {val}")

    summary_lines.append("")
    waste_fired = metrics.get("waste_fired", [])
    if waste_fired:
        summary_lines.append("⚠️ 発火した無駄パターン:")
        for w in waste_fired[:3]:
            summary_lines.append(f"  🔴 {w['description']}")
            summary_lines.append(f"     → {w['suggestion']}")
    else:
        summary_lines.append("✅ 無駄パターンの発火なし")

    ergo = metrics.get("ergo", {})
    if ergo:
        summary_lines.append("")
        summary_lines.append("🦴 姿勢負荷:")
        trunk = ergo.get("trunk_risk_ratio", 0)
        shoulder = ergo.get("shoulder_risk_ratio", 0)
        summary_lines.append(f"  • 腰屈曲リスク率: {trunk:.1%}")
        summary_lines.append(f"  • 肩挙上リスク率: {shoulder:.1%}")

    # Timeline data
    timeline_md = "| # | 開始(s) | 終了(s) | ラベル | 時間(s) |\n|---|---------|---------|--------|--------|\n"
    for i, lbl in enumerate(labels[:20]):
        dur = lbl["end_sec"] - lbl["start_sec"]
        timeline_md += f"| {i+1} | {lbl['start_sec']:.1f} | {lbl['end_sec']:.1f} | {lbl['label']} | {dur:.1f} |\n"

    return "\n".join(summary_lines), timeline_md, str(pdf_path), str(xlsx_path), str(project_dir)


# --- Gradio UI ---
with gr.Blocks(
    title="WorkStudy AI — Therbligs + MOST",
    theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
    css="""
    .main-header { text-align: center; margin-bottom: 20px; }
    .main-header h1 { color: #2563eb; font-size: 28px; }
    .main-header p { color: #64748b; }
    """
) as demo:
    gr.HTML("""
    <div class="main-header">
        <h1>🏭 WorkStudy AI</h1>
        <p>Therbligs + MOST互換 動作分析システム — 6工程対応</p>
    </div>
    """)

    with gr.Row():
        # Left Panel
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ 設定")
            video_input = gr.Video(label="動画アップロード (MP4)")
            template_select = gr.Dropdown(
                choices=list(TEMPLATE_CHOICES.keys()),
                label="工程テンプレート",
                value=list(TEMPLATE_CHOICES.keys())[0] if TEMPLATE_CHOICES else None
            )
            run_btn = gr.Button("▶ 解析実行", variant="primary", size="lg")

            gr.Markdown("### 📁 出力ファイル")
            pdf_output = gr.File(label="PDF レポート")
            xlsx_output = gr.File(label="Excel レポート")
            project_path = gr.Textbox(label="プロジェクトフォルダ", interactive=False)

        # Center + Right Panel
        with gr.Column(scale=2):
            gr.Markdown("### 📊 解析結果")
            result_summary = gr.Textbox(
                label="KPI サマリ & 改善提案",
                lines=18,
                interactive=False
            )
            gr.Markdown("### ⏱ タイムライン")
            timeline_display = gr.Markdown(
                value="*解析を実行すると、セグメント別タイムラインが表示されます*"
            )

    run_btn.click(
        fn=run_analysis,
        inputs=[video_input, template_select],
        outputs=[result_summary, timeline_display, pdf_output, xlsx_output, project_path]
    )

app = gr.mount_gradio_app(app, demo, path="/")
