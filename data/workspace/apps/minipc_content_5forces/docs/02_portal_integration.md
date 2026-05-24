# 02_portal_integration - Portal統合案

## 追加するカード

カード名:

```text
Content 5-Forces Gate
```

## 推奨配置

既存カードの前段に配置します。

```text
Content 5-Forces Gate
  ├─ note生成
  ├─ Kindlebook生成
  ├─ YouTube生成
  ├─ TikTok生成
  └─ ミニゲーム生成
```

## 入力項目

| 項目 | 例 |
|---|---|
| title | NEXIV測定データをExcel VBAで検査成績書へ自動転記する方法 |
| target_audience | 製造業の品質保証担当者 |
| pain | 測定データ転記ミス、成績書作成時間、属人化 |
| proof | 実務で使っている変換Excel、NEXIV出力、品質帳票 |
| unique_angle | 現場の検査成績書・測定機データ・IATF要求をつなげる |
| preferred_platform | note / kindle / youtube / tiktok / minigame |

## 出力項目

| 項目 | 意味 |
|---|---|
| total_score | 0〜100点 |
| decision | 採用 / 小さく検証 / 保留 / 捨てる |
| platform_recommendation | note, kindle, youtube, tiktok, minigame の推奨 |
| risks | 競合、代替、外部依存などの懸念 |
| next_actions | 次にやること |
| outline | 記事・動画・本の構成案 |

## API連携

FastAPIサーバー起動後、Portalから以下へPOSTします。

```text
POST http://localhost:8765/evaluate
```

サンプルJSON:

```json
{
  "title": "NEXIV測定データをExcel VBAで検査成績書へ自動転記する方法",
  "target_audience": "製造業の品質保証担当者",
  "pain": "転記ミス、工数、属人化",
  "proof": "NEXIV出力、検査成績書、VBA実務",
  "unique_angle": "品質保証の現場で使える実装例",
  "preferred_platform": "note"
}
```
