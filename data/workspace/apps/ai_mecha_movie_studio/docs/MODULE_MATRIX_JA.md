# モジュール役割表

| 分野 | 主候補 | ZIP内の接続方針 |
|---|---|---|
| 高速モーション転送 | SCAIL-2 | ComfyUI API Format JSON |
| 3D生成 | PartCrafter / Hunyuan3D | 独立環境または3DAIGC-API |
| 部品解析 | PartField | 独立サービス候補 |
| AutoRig | SkinTokens/TokenRig | 独立サービス候補 |
| 参考動画→3D動作 | Puppeteer | 独立サービス候補 |
| 3D自動処理 | Blender | Headless Python |
| TTS/声設計 | VoxCPM2 / Qwen3-TTS | localhost API推奨 |
| 音楽 | ACE-Step 1.5 | ComfyUIまたは独立API |
| 効果音/Foley | HunyuanVideo-Foley | ComfyUIまたは独立API |
| LipSync/顔 | Audio2Face / MediaPipe / MuseTalk | 個別サービス |
| 編集 | Remotion | Node/npx |
| 最終処理 | FFmpeg | ローカルCLI |
