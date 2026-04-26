# ARCHITECTURE

## 構成レイヤ
1. Windows ホスト
2. WSL2 Ubuntu
3. Python venv または Docker
4. ComfyUI
5. ACE-Step-ComfyUI custom nodes
6. ACE-Step model assets
7. Portal / Clawstack 統合

## 推奨段階導入
- Phase 1: ComfyUI + ACE-Step を単体動作
- Phase 2: Docker Compose 化
- Phase 3: Portal card 追加
- Phase 4: 将来の自動パイプライン化（動画生成AIとの接続）

## URL 例
- ComfyUI: http://127.0.0.1:8188
- Portal card stub: http://127.0.0.1:8099
