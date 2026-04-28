# RAG連携計画

## 登録すべき文書

- 限度見本
- 不良写真帳
- QC工程表
- 検査基準書
- 図面
- 過去不具合報告書
- 5Why
- 是正処置報告書
- 内部監査指摘
- 顧客クレーム履歴

## Qdrant推奨コレクション

```text
quality_defect_knowledge
inspection_standards
process_conditions
customer_requirements
```

## メタデータ

```json
{
  "part_no": "品番",
  "process": "プレス",
  "defect_type": "キズ",
  "customer": "顧客名",
  "revision": "版数",
  "confidentiality": "internal"
}
```
