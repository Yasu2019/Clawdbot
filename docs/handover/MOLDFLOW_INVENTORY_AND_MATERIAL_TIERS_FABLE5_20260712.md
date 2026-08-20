# Moldflow 棚卸しマップ + 材料データ3層分離設計

作成: 2026-07-12 Fable5(Cowork)
前段: `MOLDFLOW_FABLE5_INVESTIGATION_HANDBACK_20260712.md`(引継ぎ受領) / T019・P025確認済み
位置づけ: 引継ぎポイント①②(追跡先固定・ポート整合)は本書で完了。③(材料3層)は設計を提示(実装は承認後)。

## 0. 品質分析(要点)

- **QC工程表**: ①必読(T019/P025)→②文書読解(STEP1-4/精度計画/ブリッジ)→③現物コード突合→④乖離抽出→⑤設計提示→⑥ユーザー承認ゲート
- **FMEA主要項目**: 文書と現物の乖離を見逃す(対策: 全パスをコードで実在確認済み) / 商用カード混入(対策: tier3は器のみ・取込に承認ゲート) / サンドボックスからTailscale不達なのにDynabook作業を計画する(対策: 経路制約を明記、ホスト実行エージェントへ委譲)
- **なぜなぜの事前想定**: 「精度が上がらない」→ 材料係数が一般値 → L6実測相関が未着手 → **実測データ提供がボトルネック**(本書§4)

## 1. 棚卸しマップ(文書 vs 現物、2026-07-12静的確認)

### 1.1 アプリ本体(追跡先の固定 — 引継ぎポイント①)

| 要素 | 実体 | 状態 |
|---|---|---|
| UI | `data/workspace/apps/moldflow_cae_studio/{index.html, app.js}` | 実在。portal(8088)のカードからリンク |
| API | `scripts/moldflow_cae_studio_api.py` (619行, http.server直) | 実在。`DEFAULT_PORT=8776` |
| 再起動 | `scripts/restart_moldflow_studio_api.bat` (T056対応v2: kill-by-port) | 実在 |
| ベースライン | STEP1でgit commit済(それ以前は未追跡だった) | 済 |

**ポート整合(引継ぎポイント②) → 不整合なし。** `app.js` の `API_DEFAULT="http://127.0.0.1:8776"` と API側 `DEFAULT_PORT=8776` が一致。8088はUI配信(portal)、8776はAPI。文書の「UI 8088 / API 8776」の記述どおりで矛盾は解消。

### 1.2 API エンドポイント(現物コードから)

- GET: `/health` `/api/bbox` `/api/materials`(内蔵プリセット3種) `/api/solver-landscape` `/api/golden-case` `/api/learned-params` `/api/maturity` `/api/golden-error-trend`
- POST: `/api/upload-step` `/api/gate-advice`(STEP4 Gate Advisor) `/api/preview` `/api/defect-preview` `/api/export-job`

### 1.3 proxy solver・支援モジュール群(scripts/)

| モジュール | 役割 | 状態 |
|---|---|---|
| `cae_te_engine.py` (5100行) | 充填proxy solver本体(T&Eエンジン、質量収支KPI L5コード実装済) | 実在。L5発効はLAVIE配布待ち |
| `moldflow_step_case_builder.py` | STEP→ケース生成 | 実在 |
| `moldflow_cavity_mesh.py` / `moldflow_closed_cavity.py` | キャビティメッシュ/閉キャビティ | 実在 |
| `moldflow_golden_case.py` | ゴールデンケース(spec: `data/cae_te_workspace/samples/moldflow/golden_plate_case.json`) | 実在 |
| `moldflow_gate_advisor.py` | ゲート位置決定論スコアリング(STEP4 MVP、テスト12件PASS記録) | 実在。平板bbox近似・L/t限界は実測未校正 |
| `resin_fill_param_learner.py` | learned params | 実在 |
| `moldflow_doe.py` / `moldflow_quick_screen.py` / `moldflow_fill_video_telegram.py` | DOE/スクリーニング/通知 | 実在 |

### 1.4 精度軸の現在地(`docs/moldflow_accuracy_l3_to_l10_te_plan.md`)

- **L3(代理KPI)=現在地**。L4は健全試行100件蓄積(自動)、**L5はコード実装済・発効待ち**。
- **L6(実測相関1件)が最重要ボトルネック=ユーザー実測データ提供が必要**(ショートショット系列写真+重量 / 充填時間実測 / または文献スパイラルフロー表のいずれか1つ)。
- 「Moldflow同等精度」の主張は禁止(相関証跡なし) — 引継ぎポイント⑤どおり。

### 1.5 MCPブリッジ / Dynabook(実物Moldflow Insight 2010)

- ブリッジ: `data/workspace/moldflow_bridge/moldflow_mcp_server.py` — Synergy COM **read-only**(`analysis_enabled=false`、書込は`MOLDFLOW_ENABLE_WRITE_OPERATIONS=1`必須)。テスト/スモーククライアント/インストーラ同梱。
- Dynabook (DESKTOP-UOVCG4T / Tailscale 100.98.133.40 / Insight 2010): RDPは認証まで到達、**黒画面が残件**(`fEnableWddmDriver=0`+再起動が未実施の修正)。satelliteワーカー:5683は稼働未確認。
- **経路制約(重要)**: Cowork(Claude)サンドボックスからTailscale網へは**到達不可**(検証済)。Dynabook作業はホスト実行エージェント(Codex等)またはユーザー手動が前提。
- write解禁条件(未解決→提案): ①COM read-onlyプローブ(readiness_gate)連続PASS ②操作対象を使い捨てstudyファイルに限定 ③ユーザー明示承認、の3点成立時のみ環境変数を付与。

## 2. 材料データ3層分離の設計(引継ぎポイント③④ — 実装は承認後)

### 2.1 現状(混在の実態)

| 現物 | 内容 | 問題 |
|---|---|---|
| `engines/fea/materials.json` | 構造材8種(CuSn6, PBT_GF30等) — FEA用 | 成形解析用ではない。層ラベルなし |
| `MATERIAL_PRESETS`(api.py内ハードコード) | pp/abs/pc_generic(3種・一般値) | **コード内埋込**でデータ管理外。出典なし |
| Materials Project | `api_ready`(key保存なし・ミラー禁止の制約記載済) | 未接続(準備のみ) |
| 商用Moldflowカード | **未導入・痕跡なし** | 導入時の受け皿と承認ゲートが無い |

### 2.2 設計: 3層 + 台帳(visual_inspection_aiのデータセット台帳パターンを踏襲)

```
data/materials/
  registry.yaml            # 全カードの台帳(層・出典・ライセンス・承認・ハッシュ)
  tier1_general/           # 一般文献値(pp_generic等)。出典필記載。自由に使用可
  tier2_public/            # 公開データ(Materials Project個別取得・文献値)。ToS/引用条件を台帳に記録。ミラー禁止
  tier3_commercial/        # ライセンス許諾済み商用カードの「器」。初期状態は空+README(取込条件)のみ
```

- **registry.yaml スキーマ**: `id / name / family(PP,ABS,PC…) / tier(1|2|3) / source{type,citation,url} / license{name,commercial_use,evidence_path} / user_approved / sha256 / properties_file / validation{golden_case_refs}`
- **カードスキーマ(properties)**: `rheology(cross_wlf: n,tau*,D1..D3,A1,A2t) / pvt(Tait係数) / thermal(k,cp,T_melt,T_mold,T_eject) / shrinkage`。一般プリセットは現行キー(polymer_nu等)を併記し後方互換。
- **ガードレール**:
  - tier3は `user_approved: true` + `license.evidence_path`(許諾記録)が無い限りローダーが拒否(fail-closed、T018系統)
  - tier3実データはgit管理外(.gitignore)+SHA256を台帳に固定
  - Materials Projectは「小さな個別クエリのみ・DBミラー禁止・キー値のログ出力禁止」を台帳の制約欄に明記(既存status.jsonの制約を継承)
  - 商用Moldflowカードの複製・転記は行わない(ユーザーがライセンス下で提供した場合のみtier3へ)
- **ローダー/API**: 新設 `scripts/moldflow_materials_loader.py`(決定論・LLM不使用)が3層をマージし、`/api/materials` は各プリセットに `tier`/`source` を付けて返す。UIプルダウンに層バッジ表示。`MATERIAL_PRESETS` は tier1_general/polymer_presets.json へ外部化(api.pyは薄いフォールバックのみ保持)。

### 2.3 実装ステップ(承認後・各1セッション以内)

1. `data/materials/` 骨格+registry.yaml+tier1へのプリセット外部化+ローダー+テスト(既存API応答の後方互換テスト含む)
2. `/api/materials` のtier表示対応(UI変更はP022によりPlan提示→承認後)
3. tier2: Materials Project個別取得スクリプト(取得結果に出典・取得日を自動記録)
4. tier3: README(取込条件: ライセンス証跡+ユーザー承認+ハッシュ固定)のみ — 実データはユーザー提供があるまで空

## 3. 乖離・リスク(文書 vs 現物)

1. 材料プリセットが「APIコード内ハードコード」— 文書上は言及なし。§2で解消予定。
2. Gate AdvisorのL/t限界は一般目安のまま(実測未校正)— L6達成時に校正すること(STEP4自身に明記あり)。
3. Dynabook接続は「9割完了」だが最後の黒画面修正+ワーカー稼働確認が残る。**Coworkからは到達不可**のため、この2作業はユーザーまたはホスト実行エージェント担当。
4. `moldflow_gate_studio_api.py`(legacy)が併存 — portalでもlegacy表記済み。廃止判断は別途。

## 4. 次アクション(優先順)

| # | 作業 | 担当 | 備考 |
|---|---|---|---|
| 1 | 材料3層の実装ステップ1(骨格+ローダー+テスト) | Fable5(承認後) | 本書§2.3 |
| 2 | Dynabook黒画面修正(`fEnableWddmDriver=0`+再起動)→ ワーカー:5683稼働確認 | ユーザー/ホスト側エージェント | ブリッジHANDOVER記載のコマンド |
| 3 | **L6用の実測データ1点のご提供**(ショートショット系列 or 充填時間実測 or 文献指定) | ユーザー | 精度軸の最大ボトルネック |
| 4 | L5発効(LAVIE配布§0-1) | 別セッション | 精度計画書どおり |
| 5 | MCP write解禁3条件の合意 | ユーザー承認 | 本書§1.5 |
