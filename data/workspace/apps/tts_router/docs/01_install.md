# 導入手順

## 1. 展開
`C:\clawstack\openclaw_tts_full` など、clawstack-unified の横に配置します。

## 2. 環境変数
`config/.env.example` を必要に応じて `.env` にコピーし、APIキーを設定します。

## 3. 起動
```bash
docker compose up -d --build
```

## 4. Portalカード追加例
既存Portalのカード設定に下記を追加します。

```json
{
  "title": "TTS Hub",
  "url": "http://localhost:18082/tts_hub/index.html",
  "description": "現場通知・教育動画・顧客向けナレーション生成",
  "icon": "🔊"
}
```

## 5. VOICEVOX連携
VOICEVOX EngineがWindows側で `localhost:50021` にいる場合、Docker内からは `host.docker.internal:50021` を使います。
