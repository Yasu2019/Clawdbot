# 02. データ範囲とガードレール

## 2.1 学習対象
### A. 現職の品質関連
- 顧客不具合
- 仕入先回答
- 社内是正処置
- 改善活動
- PFMEA / DR / 監査関連
- 分析レポート
- 議事録
- Email

### B. 過去勤務先メール
- Foxconn
- Marunix
- その他過去案件

### C. CAE / FEM
- OpenFOAM
- OpenRadioss
- Impact
- PrePoMax / Abaqus / Code_Aster の将来拡張も想定可

## 2.2 範囲を広げるメリット
- 失敗パターンの母数が増える
- 類似トラブルの再発抑止に効く
- 「何が通用しなかったか」が残る
- 回答や対策の引き出しが増える

## 2.3 ただし無差別統合はしない
過去勤務先データは経験値を増やすが、現職案件へそのまま適用すると危険。

### 必須メタデータ
- `source_org`: 例 `Mitsui`, `Foxconn`, `Marunix`
- `confidentiality`: `internal`, `restricted`, `external_share_prohibited`
- `reuse_scope`: `same_org_only`, `cross_org_anonymized_only`, `analysis_only`
- `review_status`: `draft`, `reviewed`, `approved`

### 運用原則
1. **生メール全文は機微度高**
2. 現職と前職の生データは分離保管
3. 横断利用は「匿名化要約」または「一般化教訓」に限定
4. 対外文面自動生成時は `same_org_only` を優先
5. 元勤務先固有の社名・型番・顧客名は外部再利用禁止

## 2.4 推奨レイヤ
### Layer 1: Raw
- 元メール本文
- 元議事録
- 元CAEログ
- 元報告書

### Layer 2: Structured Facts
- ロット番号
- 現象名
- 原因候補
- 実施対策
- 失敗理由
- solver設定
- 境界条件
- 収束/非収束

### Layer 3: Generalized Lessons
- 再利用可能な一般教訓
- 社名や顧客を消した抽象知識
- 横断比較に使うのは主にこの層

## 2.5 former employer data の扱い推奨
### 可
- 「類似品質トラブルの一般教訓」
- 「こういう回答の抜けで揉めやすい」
- 「このCAE設定だと収束しにくい」

### 不可
- 具体社名・顧客情報入りで現職文面に再利用
- 元勤務先の守秘情報を現在案件に直接引用
- 契約上再利用禁止データの横流し

## 2.6 推奨実装ルール
- `cross_org_anonymized_only` のデータは `lesson_memory` に一般化して保存
- 生データは source_org ごとに分離
- 横断検索APIは `include_cross_org=false` をデフォルト
