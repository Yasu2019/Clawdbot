# Portalカード追記スニペット案

既存の `PORTAL_APPS.md` またはPortalカード定義に合わせて調整してください。

```markdown
## Circuit Simulation Hub

- Path: `/apps/circuit_sim_hub/index.html`
- Purpose: ngspice / LTspice連携による回路シミュレーション
- API: `http://127.0.0.1:8765`
- Status: local-only / experimental / QA support
- Notes:
  - 実機評価の代替ではなく設計検討補助
  - 出力ログと条件をRAG登録可能
```

Nginx静的配信例:

```nginx
location /apps/circuit_sim_hub/ {
    alias /usr/share/nginx/html/apps/circuit_sim_hub/;
    try_files $uri $uri/ /apps/circuit_sim_hub/index.html;
}
```
