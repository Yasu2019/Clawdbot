# 検証結果

検証日：2026-07-10

## 自動テスト

- pytest：7件合格、失敗0件
- 対象：寸法測定、判定しきい値、基準差分モデル、データ取得ガード、パイプライン、FastAPI

## 合成固定評価

- 評価画像：40枚
- 良品：10枚
- 合成不良：30枚（傷、打痕、バリ、シミ、ショートショット）
- Accuracy：1.000
- Precision：1.000
- Recall：1.000
- F1：1.000
- FP：0
- FN：0

これは本ZIPに含まれる単純な合成画像に対する結果であり、実製品性能を示しません。

## 処理時間

26回の合成画像検査：

- p50：約28.1 ms
- p95：約50.5 ms
- 最大：約366.1 ms
- 平均：約44.4 ms

初回モデル読込みやファイル保存を含むため、初回最大値が大きくなっています。実際のカメラ転送、産業用解像度、GPUモデル、ネットワーク、保存先を含めて再測定してください。

## Champion / Challenger

- ChampionとChallengerを同じ40枚で比較。
- 両方ともAccuracy、Recall、F1は1.000。
- 固定評価Gateは合格。
- Challengerは自動昇格していない。
- シャドー比較CSVとGate JSONを `data/reports` に保存。

## GPU

実行コンテナはCPU版PyTorchで、CUDA GPUは認識されませんでした。RTX 5060 Ti上の学習・VRAM・温度・安定性は未検証です。Windows実機で `scripts/gpu_diagnostics.py` と `scripts/train_autoencoder.py` を実行してください。

## 未検証

- 実製品の傷・打痕・バリ等の検出率
- 産業用カメラSDK連携
- テレセントリックレンズと1 µm級測定
- 長時間連続運転
- RTX 5060 TiでのGPU学習
- Anomalib各モデルの実機比較
- PLC、トリガー、排出機構との連携
- 顧客別限度見本とMSA
