# 10. Portal UI 案

## 10.1 追加ページ
作成先:
- `data/workspace/apps/learning_memory/index.html`

## 10.2 カード表示内容
- 最新品質案件
- high recurrence risk
- 未レビュー judgement
- Email 要回答論点
- 改善活動一覧
- CAE 最近の失敗 / 成功
- cross-org general lessons

## 10.3 Portalカード例
```html
<a class="card" href="/apps/learning_memory/index.html" target="_blank">
  <h3>Learning Memory</h3>
  <p>品質問題・改善活動・Email・CAEの経験蓄積</p>
</a>
```

## 10.4 UI タブ
- Quality
- Email
- Improvements
- CAE/FEM
- Lessons
- Review Queue

## 10.5 CAEタブで見たいもの
- tool別失敗件数
- error_signatureランキング
- 成功時の代表設定
- 類似失敗からの推奨修正順序
