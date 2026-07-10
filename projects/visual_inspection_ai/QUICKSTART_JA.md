# 10分で試す手順

## 1. Python

Python 3.11を推奨します。Python 3.12以降では、一部GPUライブラリの対応状況を個別確認してください。

## 2. セットアップ

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\setup_core.ps1
```

この処理は、仮想環境作成、無料ライブラリ導入、合成画像生成、SQLite初期化、基準モデル学習を行います。

## 3. 起動

```powershell
powershell -ExecutionPolicy Bypass -File .\windows\run_demo.ps1
```

ブラウザで http://127.0.0.1:8000 を開き、`data/demo/upload_samples` 内の画像を選択します。

- `normal_*.png`: 主にOK
- `scratch_*.png`: 傷候補
- `dent_*.png`: 打痕候補
- `burr_*.png`: バリ候補
- `stain_*.png`: シミ候補

REVIEWまたはNGになった画像は「要確認一覧」から確定できます。

## 4. 実画像への置換

`data/internal/demo_press_part/train/good` に同じ撮影条件の良品画像を入れ、次を実行します。

```powershell
.\.venv\Scripts\python.exe scripts\train_reference_model.py --product demo_press_part --promote
```

製品寸法・検査しきい値は `configs/products/demo_press_part.yaml` で調整します。
