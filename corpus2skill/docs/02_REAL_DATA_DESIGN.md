# 02 実データ前提設計

## 1. IATF文書

### 入力例
- IATF 16949要求事項
- 品質マニュアル
- 内部監査チェックリスト
- 製造工程監査表
- 製品監査表
- 是正処置報告書
- 改善の機会

### 推奨ツリー
```text
IATF Knowledge
├─ Clause
│  ├─ 4 Context
│  ├─ 5 Leadership
│  ├─ 6 Planning
│  ├─ 7 Support
│  ├─ 8 Operation
│  ├─ 9 Performance evaluation
│  └─ 10 Improvement
├─ Internal Rules
├─ Audit Evidence
├─ Corrective Action
└─ Training Materials
```

### ノード属性
- clause_id
- requirement_text_id
- internal_rule_id
- evidence_doc_id
- audit_question_id
- risk_level
- related_process

## 2. 図面PDF・STEP・GD&T

### 入力例
- PDF図面
- STEP/STLモデル
- 寸法測定表
- GD&TビューアHTML過去版
- 失敗・改善ログ

### 推奨ツリー
```text
Drawing Knowledge
├─ Drawing Metadata
├─ Datum System
│  ├─ Datum A
│  ├─ Datum B
│  ├─ Datum C-C
│  └─ Composite DRF
├─ Features
│  ├─ Holes
│  ├─ Claws
│  ├─ Pads
│  └─ Bending/Radius
├─ Tolerances
├─ Measurement Strategy
└─ 3D Model Mapping
```

### 注意
図面と3Dモデルは直接同一視しない。必ず以下を分けます。
- 図面上の要求
- STEP上の幾何候補
- 測定上の採用面
- AIの推定根拠
- 人間確認済みフラグ

## 3. QC工程表

### 入力例
- 工程順序
- 管理項目
- 管理値
- 測定機器
- 検査頻度
- 異常時処置
- 責任部署

### 推奨ツリー
```text
QC Process Control
├─ Product
├─ Process Flow
│  ├─ Incoming material
│  ├─ Press
│  ├─ Washing
│  ├─ Plating
│  ├─ Reflow
│  └─ Final inspection
├─ Control Items
├─ Measurement Methods
├─ Abnormal Handling
└─ Records
```

## 4. 過去不具合・是正処置

```text
Defect Knowledge
├─ Phenomenon
├─ Occurrence Process
├─ Detection Process
├─ Suspected Causes
├─ Verified Causes
├─ Corrective Actions
├─ Horizontal Deployment
└─ Effectiveness Check
```

