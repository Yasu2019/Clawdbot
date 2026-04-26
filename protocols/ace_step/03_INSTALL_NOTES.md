# INSTALL NOTES

## 公式ベース
- ACE-Step 1.5 公式本体
- ACE-Step-ComfyUI 公式ノード
- ComfyUI 公式

## 推奨実装メモ
- 最初は Python venv の方がトラブル切り分けしやすい
- 安定後に Docker 化
- Windows ネイティブより WSL2/Ubuntu の方が依存解決しやすい場面が多い

## モデル配置の考え方
- 大容量モデルは `models/ace-step/` に集約
- ComfyUI から見える位置にシンボリックリンクまたは bind mount

## 注意
- 依存ライブラリやモデル名は upstream の更新に追随して変わる可能性がある
- README と requirements は毎回確認すること
