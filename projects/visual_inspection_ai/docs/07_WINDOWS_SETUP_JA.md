# Windows運用

## コア環境

`windows/setup_core.ps1` を管理者権限なしで実行できます。Pythonランチャーがない場合はPython 3.11を先に導入してください。

## GPU環境

1. `nvidia-smi` が正常であることを確認。
2. PyTorch公式の現在の環境に合うCUDA版を導入。
3. `pip install -r requirements-gpu.txt` は参考用。競合時はPyTorch公式コマンドを優先。
4. `python scripts/gpu_diagnostics.py` を実行。

## 障害対策

- 学習チェックポイントを定期保存。
- 推論と学習のログを分離。
- CUDAエラー時は学習を停止し、CPU基準モデルで継続。
- GPUドライバー更新前に復元ポイントとバージョン記録を残す。
