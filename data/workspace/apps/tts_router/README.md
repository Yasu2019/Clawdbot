# OpenClaw TTS 完全統合パック（全部入り本気版）

目的: OpenClaw / Clawstack 環境に、用途別にTTSモデルを切り替える「TTS Router」を追加し、現場通知・教育動画・対話UI・高品質ナレーションを一体運用できるようにするための本番用テンプレートです。

## 想定環境
- Windows 11 Pro + Docker Desktop + WSL2
- clawstack-unified / OpenClaw / Portal / Node-RED / nginx 構成
- Portal: http://localhost:8088
- Node-RED: http://localhost:1880
- OpenClaw Gateway: http://localhost:18789

## 含まれるもの
- `gateway/`: FastAPI製TTS Router
- `portal/apps/tts_hub/`: Portalカード用TTS Hub画面
- `nodered/`: Node-RED連携フロー雛形
- `remotion/`: IATF教育動画・品質教育動画向けナレーション生成雛形
- `templates/`: 品質保証・IATF・現場通知用プロンプトテンプレート
- `docs/`: 導入、運用、監査対応、モデル選定ガイド
- `scripts/`: Windows/WSL用セットアップ補助
- `config/`: ルーティング設定、環境変数サンプル

## 基本方針
TTSを1つに固定せず、用途で切り替えます。

| 用途 | 推奨エンジン | 理由 |
|---|---|---|
| 現場アラート | StyleBertVITS2 / VOICEVOX | 低遅延、ローカル運用向き |
| IATF教育動画 | しきさいどりTTS / MioTTS / Fish Audio | 表現力重視 |
| 顧客向け資料 | Fish Audio / Gemini TTS | 自然さ・正確性重視 |
| 対話エージェント | Gemini TTS / Fish Audio | 会話自然性と読み精度 |
| 完全ローカル | StyleBertVITS2 / GPT-SoVITS / VOICEVOX | API費削減 |

## 最短起動
```bash
cd openclaw_tts_full
docker compose up -d --build
```

TTS Router API:
```bash
curl -X POST http://localhost:18081/tts/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"品質保証部からのお知らせです。設備異常を確認してください。","purpose":"factory_alert"}'
```

## 注意
- Fish Audio / Gemini TTS はAPIキーが必要です。
- 各商用TTSの利用規約・音声クローン規約・社外公開可否を必ず確認してください。
- 顧客提出物、教育動画、監査資料では、読み上げ原稿のレビュー工程を残してください。
