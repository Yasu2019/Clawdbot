# Integration Policy

## 基本方針

JuliaはClawstackの中核を置き換えません。
Juliaは「計算専用Worker」として追加します。

## 役割分担

| 領域 | 推奨 |
|---|---|
| Portal | 既存HTML/カード方式を維持 |
| OpenClaw Gateway | HTTP ToolとしてJulia Bridgeを登録 |
| RAG | 既存Python/Qdrant継続 |
| Node-RED | Julia API呼び出しフローを追加 |
| DOE/最適化 | Julia Worker |
| CAE前後処理 | Python + Julia |
| 帳票/Excel | Python継続 |

## 既存Clawstackへの追加方法

1. ZIPをClawstackルートに展開
2. Gitバックアップ作成
3. standalone composeで検証
4. override composeを作成
5. 既存composeと合わせて起動
6. Portalカードを追加
7. OpenClaw Tool定義を追加

## ポート

- 8096: Julia Numerical Worker
- 8097: Python Bridge

既存サービスと衝突した場合は、host側ポートだけ変更してください。
container側ポートは変更しない方が安全です。
