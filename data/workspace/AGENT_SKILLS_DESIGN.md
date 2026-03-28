# Agent Skills Design for Clawbot Docker

## Goal

この設計は、Google DeepMind / Gemini 系の `Agent Skills` に近い考え方を、現在の `Clawbot` Docker システムへローカル実装するためのものです。

狙いは次の 4 点です。

- 実装前に既存コードと既存アプリを必ず確認する
- 必要なときだけ最新情報を取得してから提案やコード生成に入る
- アプリごとの判断基準を再利用可能な手順として固定する
- 長期運用で「前に何を直したか」「どこを見るべきか」を忘れにくくする

## Why It Fits This System

この環境は単一アプリではなく、複数の専門領域が同居しています。

- 3D conversion
- DXF / FreeCAD
- QMS / IATF
- Learning Memory
- Email ingestion
- CAE / FEM / CFD
- Portal / observability

そのため、毎回ゼロから調べて実装すると重複と見落としが起きやすいです。
Skill 化すると、「まず何を読むか」「どの条件で実装するか」が安定します。

## Skill Design Principles

### 1. Research-first

Skill は、いきなりコードを書くためではなく、次の順で動くようにします。

1. 既存実装の有無を確認
2. 近いアプリや過去修正を確認
3. 必要なら最新情報を確認
4. その後に実装

### 2. Narrow scope

Skill は広すぎると使いにくいので、アプリ境界または業務境界で分けます。

悪い例:

- `engineering_skill`
- `all_quality_workflows`

良い例:

- `dxf_fcstd_skill`
- `qms_audit_skill`
- `model_html_skill`

### 3. Reuse existing assets first

新しい backend を増やす前に、既存の資産へつなぐのを優先します。

例:

- DXF -> FCStd は `apps/dxf2step` を拡張
- QMS Audit は既存 Rails / audit service を参照
- Learning Memory は `learning_engine` と `Qdrant` を参照

### 4. Safe rollout

Skill が提案する操作は、AGENTS.md の制約を守ります。

- `docker-compose.yml` の直接変更は勝手にしない
- 外付けハーネス優先
- 監視や同期は status file を残す

## Proposed Skill Set

### Priority A

最初に作る価値が高い skill です。

#### 1. `clawstack_portal_skill`

Purpose:

- Portal に新アプリや新カードを追加するときの手順を固定する

Must check first:

- `data/workspace/portal.html`
- `data/workspace/apps/`
- 既存 card / hub / app page

Workflow:

1. 似たアプリがあるか確認
2. 新規実装か hub 追加かを判定
3. Portal card を追加
4. 必要なら app landing page を追加

Use cases:

- 新規アプリ追加
- hub page 作成
- protocol pack の導線追加

#### 2. `dxf_fcstd_skill`

Purpose:

- DXF -> STEP / FCStd / FreeCAD 系の実装・改修

Must check first:

- `data/workspace/apps/dxf2step/dxf2step_api.py`
- `data/workspace/apps/dxf2step/dxf2step_worker.py`
- `data/workspace/apps/dxf_fcstd_protocol/`

Workflow:

1. 既存 `dxf2step` の出力と job 構造を確認
2. FreeCAD 側の export 可能形式を確認
3. UI / API / worker のどこを触るか決める
4. STEP / FCStd / preview / report の整合性を保つ

Use cases:

- FCStd 出力追加
- 厚み検出改善
- FreeCAD feature tree 寄りの改修

#### 3. `qms_audit_skill`

Purpose:

- QMS / IATF / audit 画面や rule-based audit を扱う

Must check first:

- `iatf_system/app/services/testmondai_quality_audit_service.rb`
- `data/workspace/audit_iatf_testmondai_quality.rb`
- `data/workspace/apps/qms_audit/`
- 必要なら `learning_engine`

Workflow:

1. 既存 audit service が流用できるか確認
2. rule-based で十分か、OCR/RAG が必要かを判断
3. 最小監査 UI を作る
4. 必要なら report JSON / Markdown と連動

Use cases:

- CSV quality audit
- QMS checklist audit
- IATF rule checks

#### 4. `model_html_skill`

Purpose:

- STEP / STL -> 3D HTML の表示品質、サイズ制御、ZIP 出力を扱う

Must check first:

- `clawstack_v2/data/work/scripts/model2html.py`
- `clawstack_v2/docker/quality_dashboard/app.py`

Workflow:

1. 既存 size profile と decimation guard を確認
2. 形状崩れの有無を先にチェック
3. profile / estimate / ZIP を含めて設計
4. UI 表示とダウンロード導線まで確認

Use cases:

- 2MB / 5MB / high quality 調整
- 形状崩れ調査
- 色分け / outline / scale UI

### Priority B

次に入れると効果が高い skill です。

#### 5. `learning_memory_skill`

Purpose:

- learning_engine, Qdrant, sync script, compare UI を扱う

Must check first:

- `clawstack_v2/docker/learning_engine/app/main.py`
- `data/workspace/apps/learning_memory/index.html`
- `data/workspace/sync_email_learning_memory.py`
- `data/workspace/sync_cae_learning_memory.py`

Workflow:

1. collection と ingest endpoint を確認
2. 既存 sync 状態を確認
3. compare/search UI と API の整合を確認
4. status file を更新する

Use cases:

- collection 追加
- compare form 追加
- email / CAE sync 修正

#### 6. `email_memory_skill`

Purpose:

- Gmail / EML / Email RAG / Learning Memory 同期を扱う

Must check first:

- `data/workspace/run_email_rag_ingest_report.py`
- `data/workspace/email_rag_ingest_runtime_status.json`
- `data/workspace/email_learning_memory_sync_status.json`

Workflow:

1. Gmail ingest が動いているか確認
2. SQLite / sync phase の失敗点を確認
3. `python` vs `python3` や path 差を確認
4. status file で復旧を確認

Use cases:

- Gmail 同期停止修正
- email thread memory 改修
- nightly ingest 改善

#### 7. `cae_learning_skill`

Purpose:

- OpenRadioss / OpenFOAM / CAE run memory の ingest と compare を扱う

Must check first:

- `data/workspace/sync_cae_learning_memory.py`
- `data/workspace/openradioss_run.log`
- `data/workspace/apps/molding_hub/`

Workflow:

1. どの solver log を取り込むか確認
2. run summary を正規化
3. `cae_run_memory` との接続を確認
4. compare/search で再利用性を確認

### Priority C

必要になったら作る skill です。

#### 8. `latest_research_skill`

Purpose:

- 新しい AI 技術や外部ツールを導入する前に、一次情報を確認する

Use cases:

- 新しい圧縮技術
- 新しい生成モデル
- 新しい 3D format / CAD tool

Workflow:

1. 一次情報優先
2. 本当にこの Docker のボトルネックに効くか判定
3. 導入しない理由も記録

#### 9. `observability_harness_skill`

Purpose:

- ハーネス監視、status file、nightly sync の保守

## Trigger Rules

Skill を呼ぶ条件の目安です。

- Portal / hub / card / launcher の話が出たら `clawstack_portal_skill`
- DXF / FCStd / FreeCAD の話が出たら `dxf_fcstd_skill`
- QMS / IATF / audit / checklist の話が出たら `qms_audit_skill`
- 3D HTML / STL / STEP / size profile の話が出たら `model_html_skill`
- memory / compare / sync / Qdrant の話が出たら `learning_memory_skill`
- Gmail / EML / email ingest の話が出たら `email_memory_skill`
- OpenFOAM / Radioss / CAE learning の話が出たら `cae_learning_skill`
- 新技術導入判断なら `latest_research_skill`

## Suggested Skill Folder Layout

`.agents/skills/` 配下に次の構成を推奨します。

```text
.agents/skills/
  byterover/
  clawstack_portal/
    SKILL.md
    references/
      portal_paths.md
  dxf_fcstd/
    SKILL.md
    references/
      dxf2step_paths.md
  qms_audit/
    SKILL.md
    references/
      qms_paths.md
  model_html/
    SKILL.md
    references/
      model2html_paths.md
  learning_memory/
    SKILL.md
    references/
      learning_engine_paths.md
```

## Example Skill Workflow Pattern

各 skill の中身は、だいたいこの型に揃えると運用しやすいです。

1. Confirm overlap
2. Read 2 to 5 key files
3. Check status or runtime artifact
4. Decide minimal safe change
5. Implement
6. Validate
7. Curate to ByteRover

## Recommended Rollout Order

### Phase 1

- `clawstack_portal_skill`
- `dxf_fcstd_skill`
- `qms_audit_skill`
- `model_html_skill`

理由:

- いま直接よく触っている領域
- 既存資産が多く、毎回の探索コストが高い

### Phase 2

- `learning_memory_skill`
- `email_memory_skill`
- `cae_learning_skill`

理由:

- 状態確認や同期確認の流れを固定すると保守が楽になる

### Phase 3

- `latest_research_skill`
- `observability_harness_skill`

理由:

- 横断的で有用だが、先に個別 skill を整えた方が設計しやすい

## Expected Benefits

- 実装前の既存調査漏れが減る
- 似た修正を毎回やり直さなくてよくなる
- 外部最新情報の取り込みが「必要なときだけ」になる
- Portal 追加や app 拡張の速度が上がる
- QMS や DXF のような専門領域で品質が安定する

## Recommended Next Action

最初に作るなら次の 3 つが効果的です。

1. `dxf_fcstd_skill`
2. `qms_audit_skill`
3. `model_html_skill`

この 3 つは、直近の実装履歴があり、具体的なファイルと判断基準がすでに揃っているためです。
