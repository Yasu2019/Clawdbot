---
title: OrcaでCursor・Antigravityを追加する手順と失敗防止
date: 2026-10-11
scope: Windows / Orca 1.4.223
verification: machine_checked_and_ui_observed
human_review: not_requested
tags: [orca, cursor, antigravity, windows, cli, incident-prevention]
---

# OrcaのAgent追加：検出・起動・既存作業の維持

## 再利用する結論

GUIアプリがインストールされていても、OrcaのAgent起動一覧に表示されるとは限らない。今回のOrcaはCursorを `cursor-agent`、Antigravityを `agy` で検出する。GUIを開く `cursor` コマンドをAgent CLIの代わりに登録しない。

Windowsで起動中のOrcaの設定ファイルを書き換えたり、Orcaを再起動したりせず、CLIの導入・PATH上の新規ランチャー追加・設定画面の「更新」で両Agentが表示された。

## 手順

1. 同じマシンの既存端末、worker、queue、scheduled task、watchdog、関連プロセスを調べる。`orca terminal list --json` のハンドル一覧を保存し、後で同じハンドルが残っていることを確認する。古い作業を年齢だけで停止・削除・再利用しない。必要な整理は対象・所有者・状態・資源影響を示し、明示承認を待つ。
2. `orca skills get orca-cli --json` で、このOrcaに一致するガイドを読む。現在の設定と検出対象コマンドを確認する。2026-10-11のビルドでは `cursor-agent` / `agy`。将来のビルドは再確認する。
3. `Get-Command cursor-agent,agy -ErrorAction SilentlyContinue` と、見つかったCLIの `--version` で実体を確認する。PATHにないだけか、未導入かを区別する。
4. Cursorは今回、既存の `Cursor/User/globalStorage/anysphere.cursor-agent-worker/agent-cli/.local/share/cursor-agent/versions/` 配下にCLIがあった。既存CLIを使い、PATH上の空いている名前で新規ランチャーを作る。既存ランチャーを上書きしない。今回のランチャーは特定バージョンを指すため、Cursor更新後にパスが残るか再確認する。
5. AntigravityのCLIがない場合は公式Windows配布を使う。取得前に既存バイナリ・作業・設定の有無を調べる。公式manifestのSHA512と実ファイルを照合してから起動する。manifestのURL・バージョン・サイズは将来変わるため固定値を最新扱いしない。
6. Orca「設定 → Agent → インストール済み → 更新」でPATHを再読込する。既定Agentや権限モードは追加目的では変更しない。
7. 「＋（新規タブ）」にCursorとAntigravityが並ぶことを実画面で確認する。CLIの `--version` 成功、UI表示、Agentの認証・実タスク成功は別の確認項目である。今回は前二者まで検証。認証やモデル実行成功は未検証。
8. 元の端末ハンドルが維持されたことを確認し、証拠と適用範囲を保存する。

公式手順: https://www.antigravity.google/docs/cli/install/

## 今回の検証結果

- Cursor CLI: `2026.10.01-e373342`。既存導入を使用し、`cursor-agent.cmd` を既存npm PATHディレクトリに追加。
- Antigravity CLI: `1.3.3`、193,113,240 bytes。公式manifestのSHA512一致後、`agy --version` 成功。
- Antigravityの新規ランチャー `agy.cmd` をnpm PATHディレクトリに追加。汎用インストーラーによる既存alias整理は実行していない。
- Orcaの「新規タブ」メニューで両項目を目視確認。
- 最終端末数8。元の8ハンドルを確認。Orcaの再起動・既存タスク整理・既存queue変更なし。
- 独立した人間レビューや認証済みAgentの実タスク検証は行っていない。導入成功をモデル性能向上と呼ばない。

## 失敗と対策

### 大きなCLIのダウンロード中断

PowerShellのWeb取得が遅く、curlでは `schannel: server closed abruptly (missing close_notify)` が出た。途中ファイルは実行せず保持し、Range取得で不足区間を回復して結合した。全体SHA512一致を必須とした。Range応答は206・指定サイズを検証する。キャッシュ回避queryで残区間が取得できたが、サーバー側の厳密な原因は未確定。

対策: 最初から `.part` 等に取得し、全体ハッシュ成功後に実行名へ切り替える。今回、途中ファイルを一時的に実行名に置いたため、Orcaは不完全なCLIでも存在検出できた。UIに表示されたことだけを導入完了の証拠にしない。

### 古いUI観測によるクイックコマンド誤起動

UI確認時の古い要素情報に基づく操作で、新規Claudeクイックコマンド端末が1つ開いた。認証切れで実作業は開始されなかった。その新規・自分の操作由来と確認した端末だけをOrca CLIで閉じ、元の8端末を再確認した。

対策: 操作ごとに現在の画面を再取得し、表示更新が落ち着いてから要素を選ぶ。サイドバーで幅が不足して「＋」が見えない場合、サイドバーを折りたたみ、見えている「＋」を確認して操作する。既存のquick commandを検証用に起動しない。プロセス名単位でのkillはしない。

### UTF-8とBeads初期化

Windows PowerShellでは日本語JSONを `Get-Content -Raw -Encoding UTF8` で読む。既定encodingでは文字化けからJSON解析が失敗した。

Beadsがないフォルダーで `bd init` を実行したところ、新規Gitリポジトリも作成された。初期化前にGit・Beadsの既存状態と副作用を確認する。別プロジェクトのBeadsに勝手に紐づけたり、既存設定を置き換えたりしない。

## 証拠と参照

- 作業記録: `artifacts/memory/orca-agents-20261011.md`
- Beads: `orca-local-dt8`
- Obsidian: `04_System_Records/Orca_Agents_20261011.md`
- 秘密情報、認証トークン、メール本文、SSH鍵はこのノウハウに含めない。

## 今後の記憶運用

ユーザーはBeads / Obsidian / auto-memory / ByteRover / graphify / GitHub / Tursoなどへのノウハウ蓄積を希望している。成功条件、失敗、修正理由、実証範囲、証拠参照を含めて保存する。保存したこと・同期したこと・再検索できたことを区別し、未接続先へ同期済みと報告しない。既存の共有ストアを再利用し、不要な恒久daemonや重複ストアを増やさない。
