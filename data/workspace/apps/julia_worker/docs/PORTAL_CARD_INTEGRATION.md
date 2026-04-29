# Portal Card Integration

## 目的

既存Portalへ「Julia Numerical Worker」カードを追加します。

## 追加ファイル

- `portal/cards/julia_numerical_worker.card.json`
- `portal/apps/julia_numerical_worker/index.html`

## 注意

既存Portalのカード管理方式が環境ごとに異なる可能性があります。
以下のどちらかで対応してください。

### パターンA: cards/*.json を自動読込するPortal

`portal/cards/` にJSONをコピーするだけです。

### パターンB: index.htmlにカードを手動追加するPortal

既存カード配列に以下を追加してください。

```json
{
  "id": "julia-numerical-worker",
  "title": "Julia Numerical Worker",
  "description": "DOE・最適化・レベラー条件探索・CAE補助用のJulia高速数値計算Worker",
  "url": "/apps/julia_numerical_worker/index.html",
  "category": "CAE / Optimization"
}
```

## API_BASEの修正

`portal/apps/julia_numerical_worker/index.html` 内の:

```js
const API_BASE = "http://localhost:8097";
```

を、実際の環境に合わせて変更してください。
