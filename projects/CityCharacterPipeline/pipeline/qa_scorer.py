"""QAスコアラー — レンダー出力画像を4項目で自動評価する

material_realism / lighting / camera / character_integration をそれぞれ1〜5点で採点。
画像がない場合はビルド結果JSONのメタデータから推定する。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4001")
LITELLM_KEY = os.getenv("LITELLM_MASTER_KEY", "yasu-fresh-token-2026-02-01")
QA_MODEL    = os.getenv("QA_MODEL", "google/gemini-2.5-flash")

PASS_THRESHOLD = 3  # 全項目がこれ以上で合格


def score_render(
    output_dir: str | Path,
    output_prefix: str = "render",
    build_result: dict | None = None,
) -> dict[str, Any]:
    """レンダー出力を評価してスコアを返す。

    Returns:
        {
            "material_realism": int,   # 1-5
            "lighting": int,           # 1-5
            "camera": int,             # 1-5
            "character_integration": int, # 1-5
            "pass": bool,
            "notes": str,
            "method": str,             # "vision" | "heuristic"
        }
    """
    output_dir = Path(output_dir)

    # レンダー画像を探す（PNG優先）
    images = sorted(output_dir.glob(f"{output_prefix}*.png"))
    if not images:
        images = sorted(output_dir.glob("*.png"))

    if images:
        return _score_via_vision(images[0], build_result)
    elif build_result:
        return _score_heuristic(build_result)
    else:
        return _score_heuristic({})


# ── Vision評価 (LLM + 画像) ──────────────────────────────────
def _score_via_vision(image_path: Path, build_result: dict | None) -> dict:
    import base64
    try:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
    except Exception as e:
        print(f"[QAScorer] 画像読み込み失敗: {e}", flush=True)
        return _score_heuristic(build_result or {})

    prompt = """あなたは3DCGレンダリングの品質評価専門家です。
以下の画像を4つの観点で1〜5点（5が最高）で採点してください。

## 採点基準

### material_realism（マテリアルリアリズム）
5: PBRテクスチャが建物・道路・金属に適切に適用されており、質感が写実的
4: テクスチャが適用されているが一部のオブジェクトが単色
3: 一部PBR、一部デフォルトマテリアル混在
2: ほとんどがデフォルトマテリアル（グレー/白箱）
1: 全て白箱またはエラー

### lighting（ライティング）
5: 自然光（太陽・空）と補助光が調和し、影とハイライトが写実的
4: ライティングは良好だがやや平坦またはオーバーエクスポーズ
3: 基本的な照明はあるが深度感に欠ける
2: 全体的にフラット、または不自然に暗い/明るい
1: 照明なし（真っ黒または真っ白）

### camera（カメラ・構図）
5: 被写体が画面中央に配置され、適切なアングルと遠近感
4: 構図は良いが若干の調整余地あり
3: 被写体は映っているが周辺に過剰な余白または切れ
2: 被写体が端に寄っているまたは大きく切れている
1: 被写体が映っていない

### character_integration（キャラクター統合）
5: キャラクターが地面に自然に接地し、周囲と溶け込んでいる（影あり）
4: 接地はしているが影または質感に若干の違和感
3: キャラクターは配置されているが浮いて見える
2: キャラクターと背景の不一致が目立つ
1: キャラクターがシーンに存在しないまたは完全に不自然

## 出力形式（JSONのみ）
{
  "material_realism": <1-5>,
  "lighting": <1-5>,
  "camera": <1-5>,
  "character_integration": <1-5>,
  "notes": "<改善点を1文で>"
}
"""

    try:
        import urllib.request
        import urllib.error
        payload = json.dumps({
            "model": QA_MODEL,
            "max_tokens": 300,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
        }).encode()

        req = urllib.request.Request(
            f"{LITELLM_URL}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LITELLM_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())

        text = data["choices"][0]["message"]["content"].strip()
        # JSON部分を抽出
        start = text.find("{")
        end   = text.rfind("}") + 1
        scores = json.loads(text[start:end])
        scores["pass"]   = _is_pass(scores)
        scores["method"] = "vision"
        print(f"[QAScorer] Vision評価完了: {scores}", flush=True)
        return scores

    except Exception as e:
        print(f"[QAScorer] Vision評価失敗 ({e}), ヒューリスティックにフォールバック", flush=True)
        return _score_heuristic(build_result or {})


# ── ヒューリスティック評価（画像なし・VisionAPI失敗時） ──────
def _score_heuristic(build_result: dict) -> dict[str, Any]:
    """build_result.json のメタデータからルールベースでスコアを推定する。"""
    errors  = build_result.get("errors", [])
    warnings= build_result.get("warnings", [])
    steps   = build_result.get("completed_steps", [])

    def has_step(keyword: str) -> bool:
        return any(keyword in s for s in steps)

    mat = 5 if has_step("materials") else 2
    lit = 5 if has_step("lighting") else 2
    cam = 5 if has_step("camera")   else 3
    cha = 5 if has_step("contact_ao") else 2

    # エラーがあれば全スコア-1
    if errors:
        mat = max(1, mat - 1)
        lit = max(1, lit - 1)
        cam = max(1, cam - 1)
        cha = max(1, cha - 1)

    scores = {
        "material_realism":      mat,
        "lighting":              lit,
        "camera":                cam,
        "character_integration": cha,
        "notes": f"ヒューリスティック推定（errors={len(errors)}, warnings={len(warnings)}）",
        "method": "heuristic",
    }
    scores["pass"] = _is_pass(scores)
    print(f"[QAScorer] ヒューリスティック評価: {scores}", flush=True)
    return scores


def _is_pass(scores: dict) -> bool:
    keys = ["material_realism", "lighting", "camera", "character_integration"]
    return all(scores.get(k, 0) >= PASS_THRESHOLD for k in keys)


def print_qa_report(scores: dict, scene_name: str = ""):
    bar = lambda v: "#" * v + "-" * (5 - v)
    print(f"\n{'='*55}", flush=True)
    print(f"  QAレポート: {scene_name}  [{('PASS' if scores.get('pass') else 'FAIL')}]", flush=True)
    print(f"{'='*55}", flush=True)
    for k in ["material_realism", "lighting", "camera", "character_integration"]:
        v = scores.get(k, 0)
        print(f"  {k:30s} {bar(v)} {v}/5", flush=True)
    print(f"\n  備考: {scores.get('notes','')}", flush=True)
    print(f"  評価方法: {scores.get('method','')}", flush=True)
    print(f"{'='*55}\n", flush=True)
