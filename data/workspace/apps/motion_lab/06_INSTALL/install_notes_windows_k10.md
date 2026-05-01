# Windows / GMKtec K10 / Clawstack向け導入メモ

## 前提
- Windows 11 Pro
- Docker Desktop + WSL2
- Clawstack unified compose
- Portal: http://localhost:8088 想定
- OpenClaw Gateway: 18789 想定
- BlenderはWindows側GUIで使う想定

## 推奨
1. このZIPを C:/clawstack_projects/cinema_motion_pipeline/ に展開
2. 既存Clawstackへはまだコピーしない
3. scripts/ を単体実行して安全確認
4. Codexへ codex_review_request.md を読ませる
5. Portalカードは採用判断後に追加

## Blender連携例
"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe" --background "staging\scene.blend" --python "03_BLENDER\scripts\cinema_motion_qa.py"
