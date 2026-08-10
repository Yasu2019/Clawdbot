# 推奨アーキテクチャ

## AIへ判断させる理由
環境ごとに、既存ComfyUIへ入れた方が良いモデルと、CUDA/PyTorchの依存が衝突するため独立環境へ分けた方が良いモデルが異なります。
そのため本ZIPでは固定方針にせず、検出結果をローカルLLMへ渡して判定させます。

## AIに許可しないこと
- 既存フォルダ削除
- pip installの自動実行
- CUDAドライバ変更
- レジストリ変更
- 既存ComfyUI custom_nodesへの自動コピー
- AI返答をshellコマンドとして実行

## 現実的な既定解
多くの環境では `hybrid` が安全です。

- 再利用: ComfyUI / FFmpeg / Blender / Node / Remotion / Ollama
- 分離: 依存競合しやすい3D AIGC / TTS / Foleyモデル
- 接続: localhost API / ファイルキュー

この方式なら、既存システムを壊さず段階的に融合できます。
