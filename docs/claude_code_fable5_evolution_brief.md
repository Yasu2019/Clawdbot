# Claude Code Fable5 レビュー依頼書 — 進化爆発の最重要ポイント

> **用途:** 高額セッション（**Fable5**）向け。全コード走査は禁止。本書の「必読15ファイル」+ 本書の質問にだけ答えさせる。  
> **作成:** 2026-06-13  
> **実装担当:** Cursor / Codex（本リポジトリ内）。Fable5 の出力は **設計判断・優先順位・ゲート設計** に限定し、実装は別セッション。

---

## 0. 北極星（1文）

ユーザーの **プレス部品 3D** から、**Moldflow 級キャビティ充填** + **Cetol 6 Sigma 級公差** + **OpenRadioss 曲げ/打ち抜き** を正しく実行し、**順送金型開発** まで到達すること。

**禁止アンチパターン（T019）:** `resin_flow`（薄管 icoFoam）を充填解析の代替にしない。Telegram に ParaView 2D |U| を Moldflow KPI として送らない。

---

## 1. セッションの目的（Fable5 に求めること）

以下 **4 ドメイン横断** で、**「次の 90 日で L レベルを 2 段以上上げる」ための最重要 3 施策** を提案してください。

| 求める出力 | 求めない出力 |
|-----------|-------------|
| アーキテクチャ上の **ボトルネック 1 本**（因果链） | 全ファイルのリファクタ案 |
| **最小 diff** で効く改善（ファイル名 + 関数レベル） | 新 Hub / 新 Docker イメージの全面置換 |
| **ゲート/KPI/DB** の fail-closed 設計 | 一般論のベストプラクティス列挙 |
| **検証 1 コマンド**  per 施策 | 100 項目チェックリスト |

**セッション時間の使い方:** 読むのは下記 **必読 15 + 任意 5** のみ。それ以外は「触らない」と明言すること。

---

## 2. 必読コンテキスト（コードより先 — 5 ファイル）

| # | パス | 読む理由 |
|---|------|---------|
| C1 | `docs/cae_north_star_and_meaning_gate_protocol.md` | 物理・カテゴリ整合の Meaning Gate |
| C2 | `docs/quality_analysis_protocol.md` | QC/FMEA/FTA 共通プロトコル |
| C3 | `data/workspace/commercial_benchmark_l10.json` | L0–L10 商用ギャップ定義 |
| C4 | `data/workspace/memory/trouble_history.md` | **[T018][T019]** 再発事故 |
| C5 | `docs/canonical_entrypoint_map_20260416.md` | 正規入口 vs レガシー除外 |

---

## 3. 必読コード（正規パイプラインのみ — 15 ファイル）

### 3-A. 動画（IATF 本番）

| # | パス | レビュー焦点 |
|---|------|-------------|
| V1 | `clawstack_v2/apps/iatf_video_factory/run_host.py` | `process_pdf` ステージ順・resume 安全性 |
| V2 | `clawstack_v2/apps/iatf_video_factory/pipeline/gate_registry.py` | ゲート単一真実・`GateBlockedError` |
| V3 | `clawstack_v2/apps/iatf_video_factory/pipeline/quality_preflight.py` | 試行前 QC/FMEA fail-closed |
| V4 | `clawstack_v2/apps/iatf_video_factory/pipeline/script_qa_gate.py` | FAIL 時 TTS/レンダ停止 |

**進化爆発の核心質問（動画）:**

> Script QA PASS 後も Visual QA / production_design で崩れる場合、**どの 1 ゲートを追加/強化すれば「Telegram 合格 = 本当に合格」** になるか？最小変更は？

---

### 3-B. DXF → 3D（Geometry 北極星の入口）

| # | パス | レビュー焦点 |
|---|------|-------------|
| D1 | `data/workspace/apps/dxf2step/dxf2step_worker.py` | LWPOLYLINE・多層合成・FCStd 保存 |
| D2 | `scripts/k10_thinkpad_dxf2step_loop.py` | 24/7 T&E・archive・品質/Telegram 連携 |
| D3 | `scripts/dxf2step_quality_gate.py` | preflight/post-mortem・`universal_growth.db` |
| D4 | `scripts/dxf2step_telegram_report.py` | 3D プレビュー + FCStd 標準送信 |

**進化爆発の核心質問（DXF2STEP）:**

> DXF→`combined.FCStd` から **Moldflow / 公差 / OpenRadioss** へ渡す際、**今欠けている 1 つのデータ契約（schema/API）** は何か？既存ファイルだけで閉じる最小案は？

---

### 3-C. 公差（Cetol 6 Sigma 級 — 現状は 1D スタックアップ中心）

| # | パス | レビュー焦点 |
|---|------|-------------|
| T1 | `data/workspace/tolerance_stackup_engine.py` | WC/RSS/MC・yield 計算 |
| T2 | `data/workspace/growth_domain_runners.py` | `run_tolerance_analysis_proxy` |
| T3 | `clawstack_v2/docker/progressive_die_hub/server.py` | `/api/tolerance-stack` UI/API |

**理論参照（任意）:** `data/scribd_downloads/moldflow_cetol_theory_pack/docs/03_tolerance_analysis_CETOL_JA.md`

**進化爆発の核心質問（公差）:**

> L10 定義（3D アセンブリ + GD&T + FreeCAD）まで行く **最短 1 スプリント** は何か？`tolerance_stackup_engine` 拡張 vs STEP フィーチャー抽出 vs 既存 progressive_die_hub 統合 — どれが ROI 最大か？

---

### 3-D. 樹脂充填（Moldflow 級 — 最優先ドメイン）

| # | パス | レビュー焦点 |
|---|------|-------------|
| M1 | `scripts/cae_te_engine.py` | **カテゴリ分岐・OpenFOAM 実行・KPI 判定**（全文不要、該当関数のみ） |
| M2 | `data/workspace/cae_workload_router.yaml` | フリート配分・`resin_fill_*` vs 禁止カテゴリ |
| M3 | `data/workspace/lavie_te_allocation_overrides.json` | 稼働カテゴリの単一真実 |
| M4 | `scripts/moldflow_closed_cavity.py` | 閉キャビティケース生成 |
| M5 | `scripts/moldflow_fill_video_telegram.py` | VOF 3D 充填 MP4 → Telegram |

**進化爆発の核心質問（樹脂）:**

> **T019 準拠** で「充填率 % / pack / short-shot リスク」を **1 つの canonical KPI JSON** に落とす設計は？`cae_te_engine` と moldflow チェーンの **接合点 1 箇所** を指定してください。

---

## 4. 横断（進化爆発の「配線」— 任意 5 ファイル）

| # | パス | 理由 |
|---|------|------|
| X1 | `scripts/cae_failure_analysis.py` | CAE 失敗の QC/FMEA/DB 標準 |
| X2 | `data/workspace/universal_growth.db` | モデル横断知識（schema 確認） |
| X3 | `data/workspace/commercial_benchmark_maturity.py` | 現 L レベル自動評価 |
| X4 | `docs/INCIDENT_LOG.md` | 再発パターン（最新 5 件） |
| X5 | `data/workspace/PROMISES.md` | P025 北極星・P017 Docker キャッシュ禁止 |

---

## 5. 読ませないもの（コスト節約）

- `ZIP_Group/extracted_*` — 参考 ZIP、本番非統合
- `scripts/ai_video_*_orchestrator.py` — IATF 本番以外
- `projects/CityCharacterPipeline/` — UE5 実験
- `data/workspace/apps/codex_ai_video_studio/**/node_modules`
- 試行用 `jobs/trial_*` 大量 DXF（サンプル 1 件で足りる）
- **`resin_flow` を Moldflow 代替とする提案** — 禁止

---

## 6. Fable5 への出力テンプレ（この形式のみ）

```markdown
## Executive Summary（3行）

## 現状 L レベル（commercial_benchmark_l10 参照）
| ドメイン | 推定 L | 根拠ファイル 1 行 |
|----------|--------|------------------|

## 進化爆発トリガー Top 3（90日）
### 1. [タイトル]
- ボトルネック（1文）
- 変更ファイル（最大3）+ 関数/ゲート名
- KPI（定量・試行前/後）
- 検証コマンド（1行）
- リスク / 触るな

### 2. ...
### 3. ...

## パイプライン配線図（ASCII or mermaid 1 枚）
DXF -> STEP/FCStd -> Moldflow KPI -> Tolerance -> OpenRadioss -> 順送金型

## 明示的に「今やらない」こと（3件）

## Cursor/Codex 実装ハンドオフ（チェックリスト 5 項目）
```

---

## 7. 実装側（Cursor）への引き継ぎルール

Fable5 の回答を受けたら、実装セッションでは:

1. **Top 1 だけ** を `bd create` で issue 化して着手
2. 新ゲートは `gate_registry` または `dxf2step_quality_gate` パターンに合わせ **artifact + fail-closed**
3. Docker `--no-cache` 禁止（P017）
4. 変更後は `commercial_benchmark_maturity.py` または該当 KPI JSON で L 上移動を確認
5. 教訓は AI メモリだけでなく **`universal_growth.db` + jsonl**

---

## 8. コピペ用プロンプト（Fable5 セッション先頭）

```
あなたは Clawstack 順送金型 CAE/品質/動画スタックの Principal Architect です。

必ず `docs/claude_code_fable5_evolution_brief.md` に従ってください。
全リポジトリ走査は禁止。必読 C1–C5 + 3-A〜3-D + 任意 X1–X5 のみ読んでください。

目的: 90日で commercial_benchmark_l10 の L を2段上げる「進化爆発」トリガー Top 3。
T019: resin_flow 代替禁止。Telegram は North Star KPI のみ。

出力は本書セクション6のテンプレのみ。一般論・全面リライト・新規マイクロサービス提案は不要。
各施策に「変更ファイル最大3」「検証コマンド1行」を必須。

特に DXF2STEP -> Moldflow -> Tolerance -> OpenRadioss の **1 つのデータ契約** を提案してください。

Top 3 の骨子が出揃った時点で、セクション6テンプレ形式の Markdown を
**直ちに** 次のパスへ書き込んで保存してください（セッション末尾まで待たない）:
  docs/fable5_evolution_advice_YYYYMMDD.md
（YYYYMMDD は今日の日付。保存後に追記があれば同ファイルを更新可）
```

---

## 9. 成功判定（このブリーフが機能したか）

| 判定 | 条件 |
|------|------|
| **成功** | Top 3 のうち 1 件が 2 週間以内に KPI JSON / ゲート artifact で検証可能 |
| **部分成功** | 配線図と「やらないこと」が明確で、誤実装コストが減った |
| **失敗** | ファイル一覧・一般論のみで、変更点と KPI が特定できない |

---

## 10. Fable5 セッション手順（貼り付け → MD 保存）

### 推奨フロー

1. **Claude Code を本リポジトリ直下で起動**（Fable5 モデル選択）
2. セクション **8 のプロンプト** を貼る（本ファイル全文の貼り付けは不要。プロンプトだけで足りる）
3. Fable5 に **必読ファイルを実際に Read** させる（プロンプト内のパスをそのまま読ませる）
4. **Top 3 が出揃った時点** で Fable5 に保存を依頼（上限到達前の取りこぼし防止）:
   ```
   セクション6テンプレに沿った回答を
   docs/fable5_evolution_advice_YYYYMMDD.md
   に書き込んで保存してください。
   ```
5. 保存後、**Cursor にその MD を渡す** → Top 1 実装

### Pro プラン / 利用枠（API 相談メモ — 2026-06-13）

| 項目 | 内容 |
|------|------|
| **無追加課金期間** | 2026-06-22 まで Fable 5 が Pro に含まれる（本日から約 9 日） |
| **6/22 以降** | 使用クレジット制・Fable 利用は上乗せ課金の見込み |
| **枠の消費** | Pro 上限内（数時間ごとリセット）。Fable 5 は高単価のため消費が速い |
| **推奨タイミング** | **利用枠リセット直後**に 1 セッション完結。途中で他 Claude 作業を挟まない |
| **2 回目レビュー** | Top 1 実装後の再レビューも使うなら **6/22 前** に逆算 |
| **実装分担** | Fable5 = 設計レビューのみ。実装・KPI 検証 = Cursor/Codex（2 週間判定は別軸） |

**推奨実行:** 週末〜6/16 週明け（枠リセット後・1 本集中）

### 注意（品質を左右する点）

| 方法 | 期待できるアドバイス品質 |
|------|-------------------------|
| **本リポジトリ内で Fable5 + 必読ファイルを Read** | **高** — ファイル名・関数・ゲートを根拠にできる |
| 本 MD 全文だけを Web チャットに貼る（コード未読） | **低〜中** — 一般論になりやすい |
| 本 MD + 必読ファイル数本を手動で同梱 | **中** — 主要判断は可能 |

### 回答 MD の保存先（命名規則）

```
docs/fable5_evolution_advice_20260613.md   # 例
```

Cursor 側では `@docs/fable5_evolution_advice_YYYYMMDD.md` を参照すれば、Fable5 の Top 1 をそのまま実装に落とせます。

*旧ファイル名 `claude_code_grade5_evolution_brief.md` は本ファイルに統合（名称訂正: Fable5）。*

---

## 11. 実装ステータス（2026-06-13 更新 — Cursor 実装済み）

### 11-A. L ベースライン（セッション前に同梱推奨）

最新スナップショット: `data/workspace/commercial_benchmark_maturity_20260607.json`

| ドメイン | 平均 L | 備考 |
|----------|--------|------|
| MOLDFLOW | **L3.3** | integration L3、fill KPI proxy 稼働 |
| OPENRADIOSS_BLANKING | L2–3 | 固定デック → manifest スケール stub 移行中 |
| DXF2STEP | L0–1 | ThinkPad T&E 試行数が maturity エビデンスに未反映 |

**Phase2 (2026-06-13):** 7サンプル × 10mm 試行 SUCCESS。manifest アーカイブ **8/8 = 100%**（`part_geometry_contract.py --validate-archive`）。

**再生成:** `python data/workspace/commercial_benchmark_maturity.py --out data/workspace/commercial_benchmark_maturity_YYYYMMDD.json`

### 11-B. 横断データ契約（1 本に昇格）

**`part_manifest.json`** (`clawstack.part_manifest.v1`) が DXF2STEP → Moldflow / 公差 / OpenRadioss の単一 handoff。

| 下流 | 読むフィールド | 成果物 |
|------|----------------|--------|
| Moldflow | `step_path`, `physics_handoff.moldflow` | `moldflow_kpi.json` |
| 公差 | `features.nominal_dims_mm` | `geometry_source=measured` |
| OpenRadioss | `bbox_mm`, `sheet_thickness_mm` | `openradioss_handoff.json`, `manifest_deck_meta.json` |

**Phase2b (2026-06-13):** OpenRadioss 本番 `press_blanking` **SUCCESS**（`geometry_source=step_shell`, `OPENRADIOSS_PREFER_STEP_SHELL=1` 既定）。`step_to_openradioss_shell.py`: gmsh 中面メッシュ → I10 `/SHELL`、starter preflight + 失敗シェル prune + bbox 自動フォールバック。Golden: `OR-BLANK-001-S01` / `tp-dxf-44920df6`（59 shells, starter prune eid=40）。`/CNTACT` は IMPDISP テンプレのため未注入（`OPENRADIOSS_STEP_SHELL_CONTACT=1` で任意）。bbox フォールバック: `OPENRADIOSS_PREFER_STEP_SHELL=0`。`--backfill-archive` で ee58460f 等 manifest 欠落を修復。

### 11-C. OpenRadioss 必読追加（Fable5 注記 #4 対応）

| パス | 焦点 |
|------|------|
| `scripts/cae_te_engine.py` | `_run_openradioss`, `_assess_openradioss`, `_enrich_params_from_part_manifest` |
| `data/workspace/apps/dxf2step/openradioss_manifest_deck.py` | manifest → blank/V-bend `.rad` スケール stub |

### 11-D. `cae_te_engine.py` 関数名（全文読み不要）

| 関数 | 用途 |
|------|------|
| `_resolve_step_from_part_manifest` | Moldflow STEP 解決 |
| `_moldflow_cad_build` | Phase-7 CAD + gate_spec |
| `_write_moldflow_kpi_json` | canonical KPI |
| `_extract_vof_fill_kpis` | 充填率/short-shot |
| `_openfoam_skip_paraview` | T019: ParaView |U| スキップ |
| `_run_openradioss` | OpenRadioss 実行 + manifest deck |

### 11-E. 検証コマンド（実装完了チェック）

```powershell
python scripts/part_geometry_contract.py --validate-archive data/workspace/thinkpad_dxf2step_history
python scripts/cae_te_engine.py --category resin_fill_cad --once --dry-run --part-manifest data/workspace/thinkpad_dxf2step_history/tp-dxf-44920df6/part_manifest.json
python scripts/cae_te_engine.py --category press_blanking --once --dry-run --part-manifest data/workspace/thinkpad_dxf2step_history/tp-dxf-44920df6/part_manifest.json
python scripts/k10_dxf2step_manifest_batch.py --thickness 10
```

### 11-F. フリート・ジョブ配分（各PC）

**正規参照:** [`docs/fleet_job_allocation_20260613.md`](fleet_job_allocation_20260613.md)

| ノード | 主ジョブ |
|--------|----------|
| K10 | オーケ、IATF 動画、Scribd/Web、OR heavy フォールバック、公差 gap |
| メイン LAVIE | OpenFOAM 充填（第一候補） |
| 赤 LAVIE | OpenRadioss 打ち抜き/曲げ、非CAE オフロード |
| ThinkPad | DXF→FCStd/STEP + manifest |
| G3 | n8n スケジュール |
| Dynabook | CAE dry-run / shell |

**E2E:** `python scripts/fable5_manifest_e2e.py --part-manifest ...`

**2026-06-13 policy-clean E2E SUCCESS** (`fable5_e2e_20260613_222614`, `--require-red-lavie`):

| Step | Host | Verdict |
|------|------|---------|
| manifest_validate | K10 | OK |
| tolerance | K10 | PASS (L2 GDT proxy) |
| resin_fill_cad | **LAVIE** | SUCCESS (~40s, VOF fill) |
| press_blanking | **red_lavie** | SUCCESS (~24s, manifest) |

`policy_degraded: false` — 3本柱すべて所定ホストで完走。

**Red LAVIE 運用:** worker :5682 + OR Docker image + monitor :8111 + Startup VBS。K10 からの bringup は `red_lavie_bootstrap_from_k10.ps1`（K10 `:8123` 経由ダウンロード）。

**次フェーズ（2026-06-13 完了）:** GD&T **L4** PMI（`5.step` -> 2 holes）+ **L10** assembly/Cp/Cpk/factory KPI（`tolerance_l10_assembly.py`）。
**残（商用フル）:** 弾性接触ソルバ / ECN-CAPA 自動起票 / CMM 実測フィード — `tolerance_cetol_full.py` スキャフォールドは **DONE**。
- Cetol Hub: `/api/tolerance-stack/preview-manifest`, `/from-manifest`, `/upload-manifest` + UI manifest 読込
- IATF: `visual_qa.py` checklist 統合、`run_host.py` gate_registry fail-closed
- Red LAVIE: `scripts/fable5_red_lavie_or_rerun.py` (offline 時は `RED_LAVIE_OFFLINE` レポート)

**Opus 4.8 報告書:** [`docs/fable5_opus48_status_report_20260613.md`](fable5_opus48_status_report_20260613.md)

*End of brief.*

