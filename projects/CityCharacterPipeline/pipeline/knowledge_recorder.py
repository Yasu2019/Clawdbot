"""知識記録モジュール — QC工程表・FMEA・レンダーパラメータをDB・Markdownに保存

PostgreSQL (sim_trials DB) + ByteRover context-tree + Markdownファイルの3箇所に記録する。
AIでなくても同等結果を再現できるように、パラメータ・スコア・教訓を完全記録する。
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# 日本語Windows(cp932)でのpsycopg2エンコードエラーを防ぐ
os.environ.setdefault("PGCLIENTENCODING", "UTF8")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT      = Path(__file__).resolve().parents[3]
BRV_DIR   = ROOT / ".brv" / "context-tree" / "infrastructure" / "city_character_pipeline"
LESSONS_PATH = ROOT / "projects" / "CityCharacterPipeline" / "knowledge" / "lessons.md"
FMEA_PATH    = ROOT / "projects" / "CityCharacterPipeline" / "knowledge" / "fmea_log.md"
QC_PATH      = ROOT / "projects" / "CityCharacterPipeline" / "knowledge" / "qc_process_chart.md"

_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:change_me@127.0.0.1:5432/sim_trials",
)
_DB_RETRY_WAIT_SEC = [5, 15, 30]   # 接続バックオフ: 5s → 15s → 30s


def _connect_with_retry():
    """バックオフでPostgreSQLに接続する。全失敗時はdb_self_healerの診断を経て1回追加リトライ。"""
    import psycopg2
    from db_self_healer import diagnose_and_fix, save_to_pending_queue

    last_err: Exception | None = None
    for attempt, wait in enumerate(_DB_RETRY_WAIT_SEC, 1):
        try:
            return psycopg2.connect(_DB_URL, client_encoding="utf8")
        except Exception as e:
            last_err = e
            print(
                f"[KnowledgeRecorder] DB接続失敗 (attempt {attempt}/{len(_DB_RETRY_WAIT_SEC)})"
                f" -- {wait}s後に再試行",
                flush=True,
            )
            time.sleep(wait)

    # 全リトライ失敗 → LLM診断 + 自動修正 → 修正後1回だけ追加リトライ
    print("[KnowledgeRecorder] 全リトライ失敗。LLM自己診断を実行...", flush=True)
    diagnosis, was_fixed = diagnose_and_fix(str(last_err))
    if was_fixed:
        print("[KnowledgeRecorder] 修正実施済み。最終リトライ...", flush=True)
        try:
            return psycopg2.connect(_DB_URL, client_encoding="utf8")
        except Exception as e:
            last_err = e
            print(f"[KnowledgeRecorder] 最終リトライも失敗: {e}", flush=True)

    raise last_err  # type: ignore[misc]


# ── PostgreSQL ────────────────────────────────────────────────
def _ensure_table():
    try:
        conn = _connect_with_retry()
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS city_render_trials (
                id            SERIAL PRIMARY KEY,
                scene_name    TEXT,
                project_tag   TEXT,
                config_json   JSONB,
                qa_scores     JSONB,
                render_params JSONB,
                fmea_json     JSONB,
                output_path   TEXT,
                render_sec    FLOAT,
                status        TEXT,
                lessons       TEXT,
                created_at    TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"[KnowledgeRecorder] DB table ensure failed: {e}", flush=True)


def record_trial(
    scene_name: str,
    config: dict,
    qa_scores: dict,
    fmea: dict,
    output_path: str,
    render_sec: float,
    status: str = "done",
    lessons: str = "",
) -> int | None:
    """レンダー試行をDBに記録して row_id を返す。
    LLM診断付き自動修正リトライ → 最終失敗時はペンディングキューに退避。
    """
    from db_self_healer import save_to_pending_queue

    _ensure_table()
    render_params = {
        "engine":  config.get("render",{}).get("engine","CYCLES"),
        "samples": config.get("render",{}).get("samples", 64),
        "device":  config.get("render",{}).get("device","CPU"),
        "resolution": config.get("camera",{}).get("resolution",[1920,1080]),
        "hdri":    config.get("lighting",{}).get("hdri_path","procedural"),
        "sun_energy": config.get("lighting",{}).get("sun",{}).get("energy", 5.0),
        "ambientcg_building": config.get("materials",{}).get("building_texture",""),
        "contact_ao_enabled": config.get("contact_ao",{}).get("enabled", True),
        "character_height_m": config.get("character",{}).get("height_m", 18.0),
    }
    # INSERT パラメータ（ペンディングキュー共通フォーマット）
    payload = dict(
        scene_name  = scene_name,
        project_tag = config.get("knowledge",{}).get("project_tag",""),
        config_json = json.dumps(config, ensure_ascii=False),
        qa_scores   = json.dumps(qa_scores, ensure_ascii=False),
        render_params = json.dumps(render_params, ensure_ascii=False),
        fmea_json   = json.dumps(fmea, ensure_ascii=False),
        output_path = output_path,
        render_sec  = render_sec,
        status      = status,
        lessons     = lessons,
    )
    try:
        conn = _connect_with_retry()
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO city_render_trials
              (scene_name, project_tag, config_json, qa_scores, render_params,
               fmea_json, output_path, render_sec, status, lessons)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING id
        """, tuple(payload.values()))
        row_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        print(f"[KnowledgeRecorder] DB recorded: id={row_id}", flush=True)
        return row_id
    except Exception as e:
        # LLM診断 + 自動修正後のリトライも失敗 → ペンディングキューに退避
        print(f"[KnowledgeRecorder] DB write 最終失敗: {e}", flush=True)
        save_to_pending_queue(payload)
        return None


# ── Markdown記録 ──────────────────────────────────────────────
def _append_md(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)


def record_qc_process_chart(scene_name: str, config: dict):
    """QC工程表をMarkdownに記録する。"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    content = f"""
## QC工程表 — {scene_name} ({ts})

| # | 工程 | 管理特性 | 管理方法 | 判定基準 | パラメータ |
|---|---|---|---|---|---|
| 1 | Config読み込み | YAMLスキーマ検証 | 必須フィールド確認 | 全フィールド存在 | — |
| 2 | Blend読み込み | シーン整合性 | オブジェクト数確認 | ≥1オブジェクト | blend={config.get('blend_source','new')[:40]} |
| 3 | マテリアル強化 | PBRテクスチャ適用 | ambientCGアセット | 全建物・道路に適用 | bldg={config.get('materials',{}).get('building_texture','')} rough={config.get('materials',{}).get('roughness_override',0.7)} |
| 4 | ライティング | 照明設定 | HDRI + 太陽 + Fill | 日中自然光 | sun_energy={config.get('lighting',{}).get('sun',{}).get('energy',5.0)} hdri={config.get('lighting',{}).get('hdri_path','procedural')[:30]} |
| 5 | 接地AO | キャラ接地影 | ShadowCatcherプレーン | 足元に自然な影 | r={config.get('contact_ao',{}).get('radius',3.0)} strength={config.get('contact_ao',{}).get('strength',0.6)} |
| 6 | カメラ | 構図・レンズ | Cycles Camera | 被写体が中央 | lens={config.get('camera',{}).get('lens_mm',85)}mm res={config.get('camera',{}).get('resolution',[1920,1080])} |
| 7 | レンダリング | 画質 | Cycles {config.get('render',{}).get('samples',64)}spp | 全黒なし・ノイズ最小 | samples={config.get('render',{}).get('samples',64)} denoiser={config.get('render',{}).get('denoiser','OIDN')} |
| 8 | QAゲート | 品質スコア | 4項目スコアリング | 全項目≥3/5 | 自動判定 |

"""
    _append_md(QC_PATH, content)
    print(f"[KnowledgeRecorder] QC工程表記録: {QC_PATH.name}", flush=True)


def record_fmea(scene_name: str, qa_scores: dict, lessons: str = ""):
    """FMEAをMarkdownに記録する。"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    mat = qa_scores.get("material_realism", 0)
    lit = qa_scores.get("lighting", 0)
    cam = qa_scores.get("camera", 0)
    cha = qa_scores.get("character_integration", 0)

    def _row(process, fm, effect, cause, sev, occ, det, action):
        rpn = sev * occ * det
        return f"| {process} | {fm} | {effect} | {cause} | {sev} | {occ} | {det} | **{rpn}** | {action} |"

    content = f"""
## FMEA — {scene_name} ({ts})

QAスコア: material={mat} lighting={lit} camera={cam} character={cha}

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
{_row("マテリアル", "白箱（PBR未適用）", "リアリズム低下", "ambientCGアセット不在", 8, 4 if mat < 3 else 2, 3, "アセット事前ダウンロード確認 / fallback Principled")}
{_row("ライティング", "フラット照明", "深度感なし", "HDRI/太陽未設定", 7, 3 if lit < 3 else 1, 4, "Nishita Sky + sun_energy≥5 + fill2灯")}
{_row("接地AO", "DOM浮き", "不自然な接地", "Raycast miss / embed_depth不足", 9, 3, 3, "embed_depth=0.75固定 + ShadowCatcher必須")}
{_row("カメラ", "T-ポーズシルエット", "キャラ品質低下", "Mixamo未適用", 8, 2, 3, "posed FBX使用 / シルエット事前チェック")}
{_row("レンダリング", "全黒フレーム", "成果物なし", "Emission未接続", 10, 2, 2, "visual_qa gate / samples≥64")}
{_row("アニメーション", "フレーム間照明変化", "動画品質低下", "ライト設定非固定", 6, 3, 4, "全フレームで同一照明パラメータ固定")}

### 教訓
{lessons if lessons else "（今回なし）"}

"""
    _append_md(FMEA_PATH, content)
    print(f"[KnowledgeRecorder] FMEA記録: {FMEA_PATH.name}", flush=True)


def record_lesson(scene_name: str, lesson: str, qa_scores: dict, config: dict):
    """再現性のある教訓（パラメータ付き）をMarkdownに記録する。"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    passed = all(qa_scores.get(k, 0) >= 3 for k in
                 ["material_realism","lighting","camera","character_integration"])
    status = "PASS ✅" if passed else "FAIL ❌"
    content = f"""
### {ts} — {scene_name} [{status}]

**QAスコア**: material={qa_scores.get('material_realism',0)} lighting={qa_scores.get('lighting',0)} camera={qa_scores.get('camera',0)} character={qa_scores.get('character_integration',0)}

**再現パラメータ**:
- samples={config.get('render',{}).get('samples',64)}, device={config.get('render',{}).get('device','CPU')}
- sun_energy={config.get('lighting',{}).get('sun',{}).get('energy',5.0)}, hdri={config.get('lighting',{}).get('hdri_path','procedural')[:40]}
- building_tex={config.get('materials',{}).get('building_texture','')}, road_tex={config.get('materials',{}).get('road_texture','')}
- contact_ao_r={config.get('contact_ao',{}).get('radius',3.0)}, strength={config.get('contact_ao',{}).get('strength',0.6)}
- camera_lens={config.get('camera',{}).get('lens_mm',85)}mm, pos={config.get('camera',{}).get('position',[])}

**教訓**: {lesson}

"""
    _append_md(LESSONS_PATH, content)

    # ByteRoverにも記録
    if config.get("knowledge",{}).get("record_to_brv", True):
        _record_to_brv(scene_name, qa_scores, lesson, config)

    print(f"[KnowledgeRecorder] 教訓記録: {LESSONS_PATH.name}", flush=True)


def _record_to_brv(scene_name: str, qa_scores: dict, lesson: str, config: dict):
    """ByteRover context-treeにMarkdownとして記録する。"""
    try:
        BRV_DIR.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = BRV_DIR / f"{scene_name}_{ts}.md"
        passed = all(qa_scores.get(k, 0) >= 3 for k in
                     ["material_realism","lighting","camera","character_integration"])
        content = f"""---
title: CityCharacterPipeline — {scene_name}
tags: [city-render, character-placement, blender, pbr, atsugi]
created_at: {datetime.now().isoformat()}
qa_pass: {passed}
---

# {scene_name} レンダー記録

## QAスコア
- material_realism: {qa_scores.get('material_realism',0)}/5
- lighting: {qa_scores.get('lighting',0)}/5
- camera: {qa_scores.get('camera',0)}/5
- character_integration: {qa_scores.get('character_integration',0)}/5
- pass_release_gate: {passed}

## 再現パラメータ
```yaml
render_samples: {config.get('render',{}).get('samples',64)}
sun_energy: {config.get('lighting',{}).get('sun',{}).get('energy',5.0)}
building_texture: {config.get('materials',{}).get('building_texture','')}
contact_ao_radius: {config.get('contact_ao',{}).get('radius',3.0)}
camera_lens_mm: {config.get('camera',{}).get('lens_mm',85)}
```

## 教訓
{lesson}
"""
        path.write_text(content, encoding="utf-8")
        print(f"[KnowledgeRecorder] ByteRover記録: {path.name}", flush=True)
    except Exception as e:
        print(f"[KnowledgeRecorder] ByteRover write failed: {e}", flush=True)
