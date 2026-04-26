# Portalカード登録スニペット

既存Portalが静的カード配列を持つ場合、以下を追加してください。

```html
<a class="portal-card" href="/apps/auto_lp_generator/index.html">
  <h3>Auto LP Generator</h3>
  <p>品質保証・工程可視化・IATF説明向けLPを自動生成</p>
</a>
```

PORTAL_APPS.md 管理の場合:

```md
- Auto LP Generator
  - Path: /apps/auto_lp_generator/index.html
  - API: http://127.0.0.1:8010
  - Purpose: QA/IATF/工程説明LP自動生成
```
