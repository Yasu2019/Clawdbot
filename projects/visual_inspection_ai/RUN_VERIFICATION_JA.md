# ホスト側E2E検証手順 (2026-07-10 Fable5改修後・所要約10分)

## 0. 前提
Windows PowerShell / Python 3.10+。**改修点**: ECCアライメント前段 / しきい値校正済み(review 0.001199, ng 0.006574) / 校正CLI 2本

## 1. セットアップ+デモ起動
```powershell
cd D:\Clawdbot_Docker_20260125\projects\visual_inspection_ai
powershell -ExecutionPolicy Bypass -File .\windows\setup_core.ps1
powershell -ExecutionPolicy Bypass -File .\windows\run_demo.ps1
```
→ http://127.0.0.1:8000 が開く(ポータルの Visual Inspection AI カードからも到達可)

## 2. pytest全件
```powershell
.\.venv\Scripts\python -m pytest tests -q
```
期待: 全PASS(新規 test_alignment_and_calibration.py 6件含む)。サンドボックス実走済みはアルゴリズム層のみ、API層(test_api)はここが初実走

## 3. UI手動確認(受入基準PoC)
1. data\demo\upload_samples の良品→**OK**/不良→**NG**(マーキング付き)を確認
2. REVIEW一覧で1件を人手確定
3. 確定済み良品からChallenger作成→**自動昇格しない**ことを確認(手動昇格のみ)
4. CSVレポート出力

## 4. 位置ズレ耐性の体感確認(今回の改修の肝)
アップロード画像を数px平行移動した版(ペイント等で)を検査→従来は偽NG、改修後はOKのまま。
ヒートマップdiagnosticsに align_dx/dy が出る

## 5. 実部品への適用手順(次フェーズ)
1. 実カメラで良品40枚+不良各種を撮影(照明・治具固定)
2. `configs/products/_template.yaml` を複製しROI等を設定
3. しきい値校正: `python scripts\calibrate_thresholds.py --product <id> --good <良品検証dir> --bad <不良dir> --train-good <良品学習dir> --apply`
4. 寸法校正: `python scripts\calibrate_scale.py --product <id> --image <基準器画像> --ax .. --known-mm .. --apply`
5. **0.001mm級の寸法保証にはMSA(テレセントリックレンズ・校正・治具)が別途必須**(README注記)
