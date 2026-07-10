# Moldflow CAE Studio リファクタ STEP2: cgi脱却+SYNC_TMP掃除 (2026-07-10)

> 作成: Fable5。3ステップ計画の第2弾。前段: `MOLDFLOW_STUDIO_REFACTOR_STEP1_20260710.md`

## 変更内容

### 1. `import cgi` 脱却 (`scripts/moldflow_cae_studio_api.py`)

- **理由**: cgiモジュールはPython 3.13で削除済み(PEP 594)。api.err.logにDeprecationWarning実出力あり=時限爆弾
- **変更**:
  - `import cgi` / `import shutil` 除去(shutilはcopyfileobjのみで使用していた)
  - `_parse_multipart(headers, rfile)` 自前実装を追加(151行目付近)
    - boundary抽出(引用符付き対応) / Content-Length必須 / パート分解 / filename・content抽出
    - **`MAX_UPLOAD_BYTES = 512MB` 上限を新設**(cgi版に無かった安全弁。全体をメモリに読むため)
  - `_handle_upload_step` を FieldStorage → `_parse_multipart` へ置換(応答スキーマ・エラーメッセージは不変)
- **バックアップ**: `scripts/moldflow_cae_studio_api.py.bak_step2`(git管理外)

### 2. テスト新設(回帰防止)

`data/workspace/tests/test_moldflow_studio_api_multipart.py` — 7件全PASS:
バイナリ完全一致(\r\n混入) / 引用符boundary / boundary欠如 / 空ボディ / 512MB超 / 空ファイル / import cgi不在の静的検査

実行: `cd data/workspace && python -m unittest tests.test_moldflow_studio_api_multipart -v`

### 3. SYNC_TMP掃除 — **未完(手動削除待ち)**

`scripts/moldflow_golden_case_SYNC_TMP.py` はmd5で本体`moldflow_golden_case.py`と同一内容を確認済み(CHANGELOG 2026-07-07にも削除可と明記)。
AI環境からの削除は不可(権限)のため、**ユーザーがホスト側で削除**:
`del D:\Clawdbot_Docker_20260125\scripts\moldflow_golden_case_SYNC_TMP.py`

## 発効条件(重要)

**稼働中API(pid管理: apps/moldflow_cae_studio/api.pid)は旧コードのまま。** 変更発効にはユーザーによる再起動が必要:
1. 旧プロセス停止(api.pidのpidをタスクマネージャ等で終了)
2. `python D:\Clawdbot_Docker_20260125\scripts\moldflow_cae_studio_api.py` 再起動
3. 動作確認: `http://127.0.0.1:8776/api/health` → ok:true、UIからSTEPアップロード1回

## 未解決事項

- git commit が `.git/index.lock` 残骸(0バイト・7/9 22:08)でブロック中 → ユーザーがホスト側で削除後、STEP1/2をcommit
- bd起票不可環境 → 次のbd可能セッションで起票

## 次ステップ

STEP3: 機能追加(ゴールデン誤差推移+成熟度パネル) → `MOLDFLOW_STUDIO_REFACTOR_STEP3_20260710.md`
