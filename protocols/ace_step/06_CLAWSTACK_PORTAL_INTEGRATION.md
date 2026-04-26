# CLAWSTACK / PORTAL INTEGRATION

## 目的
- 既存のローカルAI基盤に ACE-Step を追加し、Portal から起動しやすくする

## 推奨方針
- 既存 compose と直結する前に、独立 compose で単独検証
- ポート衝突を避ける
- 127.0.0.1 bind を維持

## Portal card 配置例
- `apps/ace_step_hub/index.html`
- 既存カード一覧へ ACE-Step Hub を追加

## 最低限の表示項目
- 起動状態
- ComfyUI リンク
- サンプルプロンプト
- 出力フォルダへの案内
- GPU/CPU モード表示

## 将来案
- REST 経由で生成ジョブ投入
- 動画生成パイプラインに BGM 自動接続
- 監査教育動画用テンプレートと連携
