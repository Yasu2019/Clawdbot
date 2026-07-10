# ローカル外観検査・寸法測定AIシステム 完全スターター

金属プレス、樹脂成形、リード線、半田状態を対象にした、**追加費用ゼロを基本とするローカル画像検査基盤**です。

このZIPは、単なる設計書ではなく、次の機能を実装したPoCです。

- 画像アップロードによる外観判定（OK / NG / REVIEW）
- 不良候補領域のマーキング
- 基準画像との差分を用いた実動する異常検出モデル
- 画像品質チェック（ぼけ・明るさ）
- 画像からの外形幅・高さ・穴径の簡易寸法測定
- REVIEW一覧とユーザー確定
- 確定済み良品を使用したChallengerモデル作成
- Champion / Challenger管理と手動昇格
- CSVレポート出力
- SQLiteによる履歴・監査ログ
- 合成良品／不良画像の生成
- RTX GPUを使うPyTorch自動エンコーダーのサンプル
- ONNX Runtime推論アダプター
- Anomalib CLI連携サンプル
- 外部データセットのライセンス台帳と安全ダウンロード
- Windows用セットアップ・起動・GPU診断スクリプト
- pytestによる単体・APIテスト

> 重要：0.001 mm精度はソフトウェアだけでは保証できません。テレセントリックレンズ、産業用カメラ、校正、温度・振動・治具を含む測定システムとしてMSAを実施してください。本コードの寸法測定は、光学条件確立前のアルゴリズムPoCです。

## 最短起動

Windows PowerShell:

```powershell
cd visual_inspection_ai_complete
powershell -ExecutionPolicy Bypass -File .\windows\setup_core.ps1
powershell -ExecutionPolicy Bypass -File .\windows\run_demo.ps1
```

または手動:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux: source .venv/bin/activate
pip install -r requirements-core.txt
python scripts/generate_demo_data.py
python scripts/bootstrap_demo.py
python scripts/run_api.py
```

ブラウザで `http://127.0.0.1:8000` を開きます。

## 代表的なコマンド

```bash
# 合成データ生成
python scripts/generate_demo_data.py --normal 60 --defect 30

# 基準差分モデルを学習しChampion登録
python scripts/train_reference_model.py --product demo_press_part --promote

# API起動
python scripts/run_api.py

# テスト
pytest -q

# GPU診断
python scripts/gpu_diagnostics.py

# GPU自動エンコーダー学習（PyTorch GPU版を別途導入後）
python scripts/train_autoencoder.py --product demo_press_part --epochs 20

# REVIEW出力
python scripts/export_reviews.py --format csv

# アイドル時の候補学習を1回実行
python scripts/idle_trainer.py --once
```

## 推奨運用

1. 本番検査はChampionモデルだけを使います。
2. AIが迷った画像はREVIEWへ保存します。
3. ユーザーがOK/NGと不良分類を確定します。
4. 確定済みデータが一定数たまったら、GPUでChallengerを作ります。
5. 固定テストデータでChampionと比較します。
6. シャドー評価後、人が承認した場合のみ昇格します。
7. 問題があれば旧Championへロールバックします。

## ディレクトリ

```text
configs/                 製品レシピ、アプリ設定、外部データ台帳
docs/                    要求仕様・設計・計量・学習・引継ぎ文書
src/inspection_ai/       アプリ本体
scripts/                 学習・評価・生成・診断・運用スクリプト
ui/                      ローカルWeb画面
tests/                   自動テスト
data/                    実行時データ（生成後）
models/                  Champion/Challenger/Archive（生成後）
windows/                 Windowsセットアップ・起動バッチ
agent_protocol/          ローカルLLM/Fable5用プロトコル
```

## 実運用へ進む前の必須作業

- カメラ、レンズ、照明、治具の選定
- 1ピクセル当たり寸法と視野のトレードオフ確認
- レンズ歪み・透視・倍率の校正
- 実製品の良品・限度見本収集
- 不良流出リスクに応じた検出率目標の設定
- ゲージR&R、偏り、直線性、安定性の評価
- 公開データ・モデル・依存ライブラリのライセンス確認
- 現場ネットワーク、バックアップ、ユーザー権限の設計

## 免責

本システムは開発スターターです。安全・法令・顧客品質保証に関わる最終判定を、未検証のAIだけに委ねないでください。
