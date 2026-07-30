# 候補キャラクターレンダーがBlender 5.1 EEVEE識別子不一致で失敗

- 日時: 2026-07-30 JST
- Beads: `Clawdbot_Docker_20260125-hc0l`
- 対象: `vnccs_comfyui_clawstack_pro/scripts/render_character_candidate_contact_sheet.py`
- Blender: 5.1.1
- 結果: 候補FBX読込後、レンダー設定時に停止。既存FBX・Unity資産は未変更。

## 観測事実

- エラー:
  - `TypeError: enum "BLENDER_EEVEE_NEXT" not found`
  - 有効値: `BLENDER_EEVEE`, `BLENDER_WORKBENCH`, `CYCLES`
- 既存の `build_commercial_anime_character.py` は正しく `BLENDER_EEVEE` を使用していた。
- 新規スクリプトは既存の互換実装をそのまま再利用せず、別バージョンの識別子を仮定した。
- 失敗は最初の候補、レンダー前に発生。出力レポートなし。

## 5 Why

1. なぜレンダーできなかったか: 存在しないengine enumを設定した。
2. なぜ存在しない値を使ったか: 一般的な新Blender API名を仮定した。
3. なぜローカル環境で確認しなかったか: `bpy` enumのpreflightを省略した。
4. なぜ既存成功コードを再利用しなかったか: 比較レンダーの新規実装を優先した。
5. なぜ防げたか: 既存スクリプトと `scene.render.bl_rna` の両方で事前確認可能だった。

## Fishbone / FTA

- Code: engine識別子のバージョン不整合。
- Method: 成功済み実装の再利用不足。
- Verification: Blender起動時のenum preflightなし。
- Environment: 表示バージョン5.1.1でも利用可能enumは `BLENDER_EEVEE`。
- Top event: 候補品質比較不能。
  - AND: 無効enum
  - AND: レンダー開始前の検証なし

## FMEA

| Failure mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| engine enum不一致 | 全候補レンダー停止 | 4 | 4 | 2 | 32 | ローカル列挙値を選択 |
| 成功コード未再利用 | 既知障害を再導入 | 6 | 4 | 4 | 96 | 同一環境の既存値を優先 |
| preflight不足 | FBX読込後に失敗 | 3 | 5 | 3 | 45 | 最小空シーンで設定検証 |

## 修正計画（ユーザー確認待ち）

1. engineを既存成功コードと同じ `BLENDER_EEVEE` に修正。
2. Blender 5.1で空シーンの最小起動チェックを行う。
3. 3候補を別出力ディレクトリへレンダー。
4. 画像を目視比較し、低品質候補は採用しない。
5. 修正後に `docs/INCIDENT_LOG.md` と成功・失敗知見へ証拠を追記する。

## 回復・ロールバック

- 既存FBXは読み取りのみで変更なし。
- 不完全な候補出力は採用しない。
- 新規検査スクリプト1ファイルだけが変更対象。

## Web検索判断

- 不要。ローカルBlenderが有効enumをエラーに明示し、既存成功コードも正解を示している。
