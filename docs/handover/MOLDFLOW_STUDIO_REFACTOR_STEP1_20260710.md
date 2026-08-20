# Moldflow CAE Studio リファクタ STEP1: ベースラインcommit (2026-07-10)

> 作成: Fable5。3ステップ計画「①ベースラインcommit → ②cgi脱却+SYNC_TMP掃除 → ③機能追加」の第1弾。
> 入口: `docs/handover/HANDOVER_MASTER_INDEX.md` §2.5 / 継続プロトコル: `FABLE5_CONTINUATION_PROTOCOL_V2.md`

## 目的

`moldflow_cae_studio` 一式が **git未追跡のまま** Fable5生成(〜7/7)+ChatGPT改造(7/8〜7/9)を重ねており、
バックアップゼロ = Backup Rule違反状態だった。改造(STEP2以降)前に差分基準となるベースラインを確定する。

## コミット対象(9ファイル)

| ファイル | 由来 |
|---|---|
| `data/workspace/apps/moldflow_cae_studio/index.html` (20KB) | Fable5生成+ChatGPT改造 |
| `data/workspace/apps/moldflow_cae_studio/app.js` (49KB, three.js ESM) | 同上。solver-landscape/learned-params/readinessパネルはChatGPT追加(7/8-7/9) |
| `data/workspace/apps/moldflow_gate_studio/index.html` | cae_studioへのリダイレクトstub化(統合済) |
| `scripts/moldflow_cae_studio_api.py` (:8776) | 11エンドポイント。**`import cgi`残存=STEP2で除去** |
| `data/workspace/moldflow_solver_landscape.json` | ChatGPT新設(7/8) |
| `docs/knowledge/moldflow_solver_landscape_20260708.md` | ChatGPT新設。商用ソルバ地図+ソース合法性分類 |
| `docs/moldflow_accuracy_l3_to_l10_te_plan.md` | Fable5(7/7)。精度軸L3→L10計画(マスターインデックス§2.5参照先) |
| `CHANGELOG.md` | 本エントリ追記 |
| 本ファイル | 引継ぎ |

**除外**: `api.pid` / `*.log`(デーモン一時ファイル、技術的負債#3の方針でgit管理しない)

## 検証結果

- `python3 -m py_compile scripts/moldflow_cae_studio_api.py` PASS
- `moldflow_solver_landscape.json` JSONパースPASS
- index.html/app.js 終端正常(`</html>` / `initApp();`)
- API実稼働確認: pid 29148, `/api/solver-landscape` 200応答ログあり

## 既知の問題(STEP2以降で対処)

1. `moldflow_cae_studio_api.py:12` **`import cgi`** — Python 3.13で削除済み。api.err.logにDeprecationWarning実出力 → **STEP2でmultipart自前parseへ**
2. `scripts/moldflow_golden_case_SYNC_TMP.py` — 同期一時ファイル残骸(CHANGELOG 2026-07-07に「同一内容バックアップ(削除可)」と明記あり) → **STEP2で削除**
3. Google Fonts外部依存(オフライン時フォント劣化のみ・機能影響なし) → 低優先
4. パネルのJS動的注入方式(ensure*Panel)によるHTML/JS乖離 → 低優先・大規模変更は要承認

## 運用ノート

- API変更後は**ユーザーによる再起動が必要**(pid管理: `api.pid`。K10ホスト側で稼働中のためAI環境からは再起動不可)
- bd起票は本環境から実行不可 → 次のbd可能セッションで「moldflow studio refactor STEP1-3」を起票すること

## 次ステップ

- STEP2: cgi脱却+SYNC_TMP掃除 → `MOLDFLOW_STUDIO_REFACTOR_STEP2_20260710.md`
- STEP3: 機能追加(ゴールデン誤差推移+成熟度パネル) → `MOLDFLOW_STUDIO_REFACTOR_STEP3_20260710.md`
