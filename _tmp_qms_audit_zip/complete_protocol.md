# QMS文書矛盾監査アプリ 完全版実装プロトコル

## 1. 目的

本アプリの目的は、1つのフォルダ配下に格納されたQMS文書群を横断解析し、以下を自動抽出することです。

- レビジョン不整合
- 文書名・帳票名のゆれ
- 記載項目不足
- 内容矛盾
- IATF 16949観点での不一致候補・監査リスク候補・要確認事項
- 修正提案
- 既存Docker/既存コードとの衝突リスク

本アプリは **完全自動で正誤を断定するものではなく、一次監査スクリーニング支援ツール** とします。最終判断は人が行います。

---

## 2. 対象文書

- 品質マニュアル
- 規定
- 手順書
- 標準書
- 帳票
- 記録見本
- 参考資料

想定フォルダ構成:

```text
/QMS_ROOT
  /01_品質マニュアル
  /02_規定
  /03_手順書
  /04_標準書
  /05_帳票
  /06_記録見本
  /07_参考資料
```

サブフォルダは再帰的に走査すること。  
ファイル名だけでなく、本文中の文書番号・帳票名・Rev・制定日・改訂日・部署名を優先して識別すること。

---

## 3. 対応ファイル形式

### 必須
- PDF
- DOCX
- XLSX
- XLS
- CSV
- TXT

### 可能なら対応
- PPTX
- HTML
- 画像PDF（OCR）

### 抽出ルール
- PDFはテキスト抽出優先
- 画像PDFはOCR fallback
- Excelはシート構造・見出し行・帳票項目抽出
- Wordは見出し・表・ヘッダ/フッタも可能なら抽出

---

## 4. 最重要設計方針

### 4.1 ローカルLLMに丸投げしない
以下は LLM 任せにしないこと。

- 文書番号抽出
- Rev抽出
- 制定日/改訂日抽出
- 部門名抽出
- 帳票名抽出
- 承認欄有無判定
- 保存期間候補抽出
- Excel帳票の項目抽出
- 同一文書候補の一次グルーピング
- ルールベース矛盾検出

これらは必ず Python 側の deterministic なロジックで行うこと。

### 4.2 LLMは補助役に限定
LLMの役割は以下に限定すること。

- ルールベースで検出した差分が実質矛盾か表記ゆれかの補助判定
- 差分内容の日本語要約
- 推奨修正案の文章生成
- IATF監査向けコメント生成
- 「要確認」理由の自然文生成

### 4.3 まずMVPを完成させる
優先順:
1. 取り込みが安定する
2. メタデータ抽出が再現性高くできる
3. 一覧表が出せる
4. 比較根拠が見える
5. 誤検出でも人が判断しやすい

---

## 5. 推奨アーキテクチャ

```text
Document Parsing Engine
  -> Structured Extraction Engine
  -> Rule-based Comparison Engine
  -> Candidate Scoring Engine
  -> LLM Assist Layer
  -> Report / UI
```

### 層ごとの責務

#### A. Parser層
- PDF / DOCX / XLSX / XLS / CSV / TXT 読み込み
- OCR fallback
- 生テキスト、表、セル情報、見出し情報抽出

#### B. Structured Extraction層
- 文書番号抽出
- Rev抽出
- タイトル抽出
- 帳票名抽出
- 承認欄検出
- 改訂履歴検出
- 保存期間候補抽出
- 部門名候補抽出
- 帳票フィールド一覧抽出

#### C. Rule-based Comparison層
- 文書番号一致比較
- Rev矛盾検出
- 名称ゆれ候補抽出
- 項目不足検出
- 参照文書整合チェック
- 保存期間差分検出
- 承認欄有無差分検出
- 部門名差分検出

#### D. Candidate Scoring層
- 重要度スコアリング
- High / Medium / Low分類
- LLMに回す候補の絞り込み

#### E. LLM Assist Layer
- 実質矛盾かどうかの説明支援
- 修正提案文生成
- 監査コメント生成
- 差分要約

---

## 6. システム構成方針

### 推奨構成
- Frontend: Streamlit
- Backend: FastAPI
- Document parser:
  - pdfplumber / pymupdf
  - python-docx
  - openpyxl / pandas
  - pytesseract または既存OCRスタック
- Vector/search: Qdrant（必要に応じて）
- Embedding: 既存 embedding サービス流用
- LLM: 既存ローカル/クラウド切替
- Storage: SQLite または Postgres
- Output: HTML / Excel / CSV / JSON / PDF

### コンテナ案
- qms_audit_api
- qms_audit_ui
- qms_audit_worker

既存 Qdrant / embedding / gateway がある場合はできるだけ共用すること。

---

## 7. 実装前の既存システム監査（必須）

新規実装前に、**Dockerコンテナ内および既存リポジトリに同様機能が既にないか必ず確認** すること。  
重複実装・競合・ポート衝突・DB衝突を避けるため、以下を必須ステップとする。

### 7.1 必須確認項目
- 既存 docker-compose.yml / compose.*.yml の確認
- 既存 Dockerfile の確認
- 稼働中コンテナ一覧の確認
- 使用中ポート一覧の確認
- 既存 Streamlit / FastAPI / OCR / RAG / 文書解析サービスの確認
- 既存Qdrant collection の確認
- 既存文書取込フロー（Paperless / Docling / ingest_watchdog 等）の確認
- 既存の類似アプリ（監査、文書比較、RAG、帳票解析）の確認

### 7.2 衝突回避ルール
- 同機能が既にある場合は再実装せず、まず再利用・統合を検討する
- 新規ポートは未使用番号を割り当てる
- 既存DBに直接破壊的変更を加えない
- 既存 collection / bucket / volume 名と衝突しない命名を使う
- 既存 worker / queue と責務が重なる場合は統合案を先に出す
- 既存コードを削除する前にバックアップと差分説明を作る

### 7.3 実装開始前に必ず作る資料
- existing_system_audit.md
- conflict_check_report.md
- integration_plan.md

### 7.4 既存システム監査の出力例
- 既存類似機能の有無
- 再利用候補
- 新規実装が必要な不足点
- 衝突の有無
- 統合方法
- 非推奨な重複実装

---

## 8. 文書インデックス機能

フォルダを指定して文書を一括取り込みし、各ファイルについて次を抽出すること。

### 抽出メタデータ
- file_path
- file_name
- extension
- folder_category
- detected_document_type
- detected_title
- detected_document_number
- detected_revision_raw
- detected_revision_normalized
- detected_issue_date
- detected_update_date
- detected_department
- detected_owner
- detected_approval_role
- detected_form_name
- detected_related_process
- text_length
- parse_confidence
- ocr_used

### detected_document_type 候補
- 品質マニュアル
- 規定
- 手順書
- 標準書
- 帳票
- 記録見本
- その他

分類はフォルダ名だけでなく本文内容でも補正すること。

---

## 9. 文書構造抽出機能

### マニュアル・規定・手順書系
- 章番号
- 見出し
- 責任部署
- 用語定義
- 実施手順
- 記録要求
- 保存期間
- 参照文書
- 使用帳票
- 承認フロー
- 改訂履歴

### 帳票系
- 帳票名
- 帳票番号
- Rev
- 記載欄名
- 必須/任意らしき項目
- 承認欄
- 作成者欄
- 部門欄
- 日付欄
- ロット欄
- 判定欄
- 保存先/保管年限
- 備考欄
- 参照元文書

Excel帳票はセル位置付きでフィールド抽出できるようにすること。

---

## 10. 類似文書グルーピング機能

### グルーピング条件
- 文書番号一致
- 帳票番号一致
- タイトル類似
- ファイル名類似
- 本文冒頭類似
- 項目構造類似
- ベクトル類似（必要時）

### 出したい結果
- 同一文書候補グループ
- 旧版/新版候補
- 同一帳票の派生版候補
- 名前違いの同一帳票候補

---

## 11. 矛盾検出機能

### A. レビジョン矛盾
- 同じ文書番号でRevが複数存在
- 同一フォルダに旧版らしきものが残っている
- 規定ではRev.5を参照しているが、帳票はRev.3ベース

### B. 名称ゆれ
- 内部監査是正処置報告書 / 内部監査 是正処置報告書
- 品証部 / 品質保証部
- 承認者 / 承認 / 責任者承認

### C. 記載項目不足
- 手順書に必要な記録欄が帳票に存在しない
- マニュアルで保存期間要求があるのに帳票に記載なし
- 承認要件があるのに承認欄なし

### D. 内容矛盾
- 責任部署が文書ごとに違う
- 記録保存年限が違う
- フロー順番が違う
- 判定基準が違う
- 用語定義が異なる

### E. 参照文書矛盾
- 廃止済らしき文書を参照
- 存在しない文書番号を参照
- 参照先名称が不完全

### F. 怪しい文書
- Rev不明
- 改訂履歴なし
- 文書番号なし
- 承認者なし
- 制定/改訂日のどちらか欠落
- ファイル名と本文タイトルが不一致
- 帳票名に対して項目数が極端に少ない

---

## 12. リスク評価機能

### High
- 上位文書と下位文書の直接矛盾
- 承認要件欠落
- 保存年限矛盾
- 判定基準矛盾
- 使用帳票誤参照
- Rev不一致で運用誤りの可能性大
- IATF要求との不一致候補

### Medium
- 名称ゆれ
- 部署名ゆれ
- 文言差異
- 改訂履歴不足
- 監査リスク候補

### Low
- 表記ゆれ
- 空白や見た目上の差異
- 軽微な用語差
- 要確認

---

## 13. 手順書 vs 帳票 不足項目比較エンジン（必須コア機能）

### 目的
手順書・規定・標準書で要求されている「記録項目」が、実際の帳票に存在するかを検証する。

### 入力
- 手順書 / 規定から抽出した「記録要求」
- 帳票から抽出した「フィールド一覧」

### 手順書側抽出対象
- 記録する
- 記入する
- 管理する
- 保存する
- トレースする
- 記録を残す
- ログを取る
- 記録様式

### 出力JSON
```json
{
  "type": "missing_field",
  "document_procedure": "",
  "document_form": "",
  "required_field": "",
  "found_in_form": false,
  "closest_field": "",
  "risk": "",
  "severity": "High|Medium|Low"
}
```

### 判定ロジック
- High: 手順書で必須記録、帳票に該当項目なし
- Medium: 類似項目ありだが曖昧
- Low: 表記違いのみ

### 禁止事項
- LLMだけで判断しない
- 必ず項目リスト同士で比較する

---

## 14. 内容矛盾検出エンジン（コア機能）

### 目的
文書間の実質的な矛盾を検出する。

### 対象比較
- 品質マニュアル vs 規定
- 規定 vs 手順書
- 手順書 vs 帳票
- 同一帳票のRev違い

### 比較対象項目
- 責任部署
- 承認者
- 保存期間
- 判定基準
- フロー順序
- 使用帳票
- 用語定義

### 出力JSON
```json
{
  "type": "content_inconsistency",
  "field": "",
  "document_a": "",
  "document_b": "",
  "value_a": "",
  "value_b": "",
  "difference_type": "",
  "severity": "",
  "confidence": 0.0
}
```

### difference_type
- 明確矛盾
- 解釈差
- 表記ゆれ
- 要確認

### ロジック順序
1. ルール比較
2. 正規化比較
3. 類似度比較
4. ここで初めてLLM

### LLMの役割
- difference_typeの補助判定
- 理由説明

---

## 15. 修正提案生成エンジン（LLM補助）

### 目的
検出された矛盾に対して、実務で使える修正案を提示する。

### トリガー条件
- severity = High
- またはユーザーが詳細表示した場合

### 入力
- 差分情報
- 文書A抜粋
- 文書B抜粋
- 判定結果
- 文書種別

### 出力JSON
```json
{
  "proposal_type": "",
  "recommended_action": "",
  "target_document": "",
  "priority": "",
  "reason": ""
}
```

### proposal_type
- 統一
- 追記
- 修正
- 削除
- 要確認

### 禁止事項
- 抽象的な提案
- 根拠なし提案
- 全ケースでLLM呼び出し

---

## 16. IATF要求事項整合チェック機能（必須）

### 目的
品質マニュアル、規定、手順書、帳票、記録見本の内容が、IATF 16949 の要求事項観点で不整合・不足・曖昧さを持っていないかを検出する。

### 基本方針
本機能は **IATF条文への法的断定機能ではなく、監査支援機能** とする。  
出力は次の3区分に分けること。

- IATF要求との不一致候補
- IATF監査上のリスク候補
- IATF観点で要確認

### チェック対象例
- 文書管理
- 記録管理
- 承認と改訂管理
- 変更管理
- 責任・権限の明確化
- トレーサビリティ
- 不適合管理
- 是正処置
- 内部監査
- 教育訓練
- 測定機器管理
- 製造工程管理
- 外部提供者管理

### 入力
- IATF要求事項マスタ
- 品質マニュアル抽出結果
- 規定抽出結果
- 手順書抽出結果
- 帳票項目抽出結果
- 記録見本抽出結果

### IATF要求事項マスタの持ち方
要求事項マスタは、条文全文だけでなく以下のような監査観点ルールに分解して保持すること。
- 条文番号
- テーマ
- 必須観点
- 必要になりやすい文書要素
- 必要になりやすい帳票要素
- 典型的な不備例

### 出力JSON
```json
{
  "type": "iatf_alignment_issue",
  "clause": "",
  "category": "",
  "document_id": "",
  "document_name": "",
  "issue_level": "不一致候補|監査リスク候補|要確認",
  "summary": "",
  "missing_or_conflicting_element": "",
  "evidence": "",
  "recommendation": "",
  "confidence": 0.0
}
```

### 判定ロジック
#### 第1段階: 非LLM判定
- 該当必須要素の有無確認
- 承認欄、改訂履歴、保存期間、責任部署などの有無確認
- 手順書要求と帳票項目の整合確認
- 関連文書参照の存在確認

#### 第2段階: LLM補助
- その不足が実質的にIATF観点で問題化しやすいか
- どのような監査リスクとして説明すべきか
- 修正提案文の生成

### 断定禁止
禁止:
- 「IATF違反である」と断定する
- 条文適合を100%自動判定したように見せる
- 根拠なしで不適合扱いする

必ず次のような表現を使うこと。
- 不一致候補
- リスク候補
- 要確認
- 監査上の懸念
- 追加確認推奨

---

## 17. LLM使用制限

### LLMに回してよいもの
- 「保存期間3年」と「記録は3年間保管」の表現差が同義か
- 「承認責任者」と「品質保証部長承認」が矛盾か補完関係か
- 手順書と帳票の文脈差分の説明
- 監査指摘風コメント生成
- 修正案文章の生成

### LLMに回してはいけないもの
- いきなり全文同士比較
- Rev抽出
- 文書番号抽出
- Excel列構造の初回解析
- 旧版新版の一次判定
- OCR結果の生整形だけにLLMを使うこと

### 全文投入禁止
品質文書全文を毎回LLMに投げて比較しないこと。  
必ず以下に縮約してから渡すこと。
- 文書Aの対象箇所抜粋
- 文書Bの対象箇所抜粋
- 比較対象項目名
- 抽出済みメタデータ
- ルールベース判定結果
- 判定してほしい内容

### JSON固定出力
```json
{
  "judgement": "矛盾候補|表記ゆれ候補|要確認",
  "summary": "",
  "reason": "",
  "recommendation": "",
  "confidence": 0.0
}
```

---

## 18. 正規化・抽出ロジック

### Rev抽出
例:
- Rev.1
- Rev 1
- R1
- 改訂A
- 第3版
- 第2改訂
- 版数4

原文保持 + 正規化値保持 の両方を持つこと。

### 文書番号抽出
例:
- QP-001
- QMS-8.5-02
- FRM-123
- QC-監-01
- 内監-報-02

ファイル名より本文優先。複数候補は信頼度を持たせる。

### 名称ゆれ判定
- 全角半角正規化
- 空白除去
- 記号除去
- 類義語辞書
- 日本語形態素類似
- embedding類似（必要時）

### 記載項目比較
- 承認者 / 承認 / 最終承認者
- 作成日 / 記載日 / 作成年月日
- ロット / LOT / 製造ロット

### 内容矛盾判定
1. ルールベース抽出
2. 構造化比較
3. 類似箇所検索
4. LLMで差分要約
5. 断定ではなく「矛盾候補」で登録

---

## 19. データ設計案

### documents
- id
- file_path
- file_name
- doc_type
- title
- document_number
- revision_raw
- revision_normalized
- issue_date
- update_date
- department
- owner
- text_content
- parsed_json
- created_at

### document_fields
- id
- document_id
- field_name
- field_label
- field_type
- field_required_guess
- source_location

### document_relations
- id
- source_document_id
- target_document_id
- relation_type
- confidence

### inconsistencies
- id
- type
- severity
- document_a_id
- document_b_id
- field_name
- summary
- evidence_a
- evidence_b
- recommendation
- confidence
- status

### iatf_issues
- id
- clause
- category
- document_id
- issue_level
- summary
- missing_or_conflicting_element
- evidence
- recommendation
- confidence

---

## 20. 出力仕様

### ダッシュボード
- 総文書数
- 文書種別ごとの件数
- Rev不整合件数
- 名称ゆれ件数
- 記載項目不足件数
- 内容矛盾件数
- 怪しい文書件数
- IATF関連指摘件数
- 優先度High件数

### 絞り込み
- 部門
- 文書種別
- 優先度
- 矛盾種別
- ファイル名
- 文書番号
- 帳票番号

### 一覧表出力列
- ID
- 優先度
- 矛盾種別
- 文書A
- 文書B
- 文書番号A
- 文書番号B
- RevA
- RevB
- 該当項目
- 指摘内容
- 根拠抜粋A
- 根拠抜粋B
- 推奨対応
- 部門
- ステータス
- 備考

### 詳細レポート
- 対象文書情報
- 比較対象文書
- 差分箇所
- 該当本文抜粋
- AIコメント
- 推奨修正案
- 人が判断するための注意点

### 文書別監査票
- 文書名
- 文書番号
- Rev
- 文書種別
- 所属部門
- 参照元/参照先
- 検出問題数
- High / Medium / Low
- 主な懸念点
- 推奨アクション

---

## 21. UI要件

### 必須画面
1. 取り込み画面
2. 解析実行画面
3. 結果一覧画面
4. 矛盾詳細画面
5. 文書詳細画面
6. IATF整合チェック画面
7. エクスポート画面
8. 設定画面
9. 既存システム監査結果画面

### UI要件
- 日本語UI
- ボタン名をわかりやすく
- 進捗表示あり
- エラー内容を明示
- 長文比較は折りたたみ
- 根拠箇所をハイライト
- 「これは候補であり断定ではない」と明示
- 「ルール検出」「AI要確認」「表記ゆれ候補」「実質矛盾候補」を区別表示

---

## 22. モード設計

### モードA: Rule-only
- 完全非LLM
- 最速
- 一次スクリーニング用

### モードB: Rule + Local LLM Assist
- ローカルLLMで補助説明
- 通常運用用

### モードC: Rule + External/High-grade LLM Assist
- 必要時のみ上位モデル利用
- 最終確認用
- 将来拡張前提

LLM停止時でもアプリが成立すること。

---

## 23. 実装優先順位

### Phase 1: 完全非LLM
- 文書取り込み
- テキスト抽出
- メタデータ抽出
- 帳票項目抽出
- 文書一覧
- Rev一覧
- 文書番号一覧
- 類似文書候補一覧
- 基本矛盾一覧
- 既存システム監査

### Phase 2: 軽量LLM補助
- 差分要約
- 表記ゆれ/矛盾候補の補助説明
- 推奨修正案
- 監査コメント

### Phase 3: 最適化
- キャッシュ
- 非同期ワーカー
- バッチ判定
- スコア最適化
- モデル切替設定
- n8n連携 / 定期実行

---

## 24. 推奨ディレクトリ構成

```text
qms_audit_app/
  app/
    main.py
    config.py
    ui/
      streamlit_app.py
    api/
      routes.py
    parsers/
      pdf_parser.py
      docx_parser.py
      excel_parser.py
      text_parser.py
      ocr_helper.py
    extractors/
      metadata_extractor.py
      revision_extractor.py
      document_number_extractor.py
      department_extractor.py
      form_field_extractor.py
      procedure_requirement_extractor.py
    normalizers/
      text_normalizer.py
      synonym_mapper.py
    comparators/
      revision_comparator.py
      field_comparator.py
      reference_comparator.py
      title_similarity.py
      procedure_form_gap_comparator.py
      content_inconsistency_comparator.py
      iatf_alignment_checker.py
    scorers/
      inconsistency_scorer.py
    llm/
      llm_client.py
      llm_prompts.py
      llm_schema.py
      llm_assist_service.py
    reports/
      excel_exporter.py
      csv_exporter.py
      html_reporter.py
    storage/
      models.py
      repository.py
      cache.py
    utils/
      regex_patterns.py
      logging_helper.py
      docker_audit.py
      port_check.py
  data/
    input/
    output/
    cache/
  dictionaries/
    synonyms_department.json
    synonyms_field.json
    suspicious_patterns.json
    iatf_requirements_master.json
  docs/
    existing_system_audit.md
    conflict_check_report.md
    integration_plan.md
  tests/
  Dockerfile
  docker-compose.yml
  requirements.txt
  README.md
```

---

## 25. 初期辞書

### synonyms_department.json
- 品質保証部 = 品証部
- 製造部 = 製造課
- 技術部 = 技術課

### synonyms_field.json
- 承認者 = 承認 = 最終承認者
- 作成日 = 記載日 = 作成年月日
- ロット = LOT = 製造ロット

### suspicious_patterns.json
- 改訂履歴なし
- Revなし
- 承認欄なし
- 文書番号なし
- 参照先不明
- 保存期間未記載
- 責任部署未記載

---

## 26. READMEに必ず書くこと
- 起動手順
- 入力フォルダの置き場所
- 対応ファイル形式
- OCR時の制限
- 誤検出が起きやすい例
- AI提案は最終判断ではないこと
- ログ保存場所
- レポート出力場所
- 既存Docker/既存コード監査を先に行うこと
- 衝突確認手順

---

## 27. 開発者向け禁止事項
1. LLMに全ファイル全文比較をさせること
2. ルール抽出前にLLMへ丸投げすること
3. 抽出・比較・提案をすべて1プロンプトで済ませること
4. LLM自由文をそのまま最終判定にすること
5. 根拠のない断定表現を出すこと
6. ローカルLLM必須設計にすること
7. 既存コンテナ/既存機能を確認せず新規実装を始めること
8. 既存ポート・既存DB・既存Qdrant collection に無確認で接続すること

---

## 28. Claude Codeへの最終依頼文（要約）
- 既存環境を壊さない
- Docker化
- Streamlit UI
- FastAPI backend
- PDF / Word / Excel対応
- 日本語文書対応
- ローカルフォルダ入力
- 結果を一覧・詳細・Excel/CSV/HTMLで出力
- ルールベース主体
- LLMは補助のみ
- Rule-only モードで主要機能が動くこと
- 既存Docker/既存コード監査を実装前に必ず行うこと
- collision / duplication 回避を文書化すること

---

## 29. 将来追加候補
- 文書体系図の自動生成
- 上位文書→下位文書参照関係マップ
- 帳票未整備箇所一覧
- IATF内部監査チェック支援
- 改訂時影響調査支援
- 新旧Rev比較画面
- 帳票標準テンプレート提案
- 部門別不整合傾向分析
- n8nで定期監査ジョブ化

