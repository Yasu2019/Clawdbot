# 04 RAG Integration Design

## 対象ソース
- 内部監査資料
- 是正処置報告書
- 不良解析報告書
- 作業標準書
- 客先向け説明資料（社内限定）

## 必須メタデータ
- 文書名
- 版数
- 発行日
- 作成部門
- 機密区分
- 元ファイルパス

## RAG抽出の基本ルール
- 根拠の無い補完を避ける
- 数値は元文書優先
- 不明点は `UNKNOWN` として残す
- 規格条文は要レビュー扱い

## 推奨プロンプト方針
- 先に事実抽出
- 次に教育用台本へ変換
- 最後にシーン分解

## 望ましいJSON構造
```json
{
  "title": "Internal Audit Training",
  "source_documents": [
    {
      "name": "audit_report_001.pdf",
      "version": "A",
      "confidentiality": "internal"
    }
  ],
  "facts": [
    "工程内で承認漏れが発生した",
    "是正処置としてダブルチェックを導入した"
  ],
  "unknowns": [
    "現場責任者の正式役職名"
  ]
}
```
