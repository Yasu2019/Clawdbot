# Codex Protocol Package (Report Template Edition)

このZIPは、Dockerコンテナ内のCodexへそのまま引き渡せるように作成した
「3Dモデル更新 → 既存資産調査 → 比較検討 → 詳細設計 → DR → 実装 → テスト → 最終報告」
用のプロトコル集です。

## 重要
- 文字コードは UTF-8 with BOM
- ファイル名は ASCII のみ
- ZIP 内エントリ名も ASCII のみ
- Windows / VS Code / 一般的なエディタで文字化けしにくい構成
- 日本語本文では、機種依存文字・特殊記号の多用を避けています

## 主な内容
- 01_codex_master_protocol.md
  全体統括プロトコル
- 02_codex_starter_prompt.txt
  Codex チャット欄に最初に貼る 1 本版。報告書テンプレ付き
- 03_repo_survey_checklist.md
  既存アプリ探索・融合判断のチェックリスト
- 04_decision_matrix.md
  既存機能流用 / 一部融合 / 取り込み / 保留 の判断基準
- 05_detail_design_and_dr_template.md
  詳細設計と DR で確認すべき項目のテンプレート
- 06_kinematics_hub_requirements.md
  プレス金型向けの可視化要求。localhost:8088 の kinematics_hub を活用
- 07_delivery_manifest.txt
  納品物・成果物一覧
- 08_bom_list.csv
  各ファイルの BOM 有無と先頭バイト確認
- 09_sha256_manifest.txt
  同梱ファイルの SHA-256 一覧
- 10_encoding_validation.txt
  文字コード確認メモ
- 11_codex_report_template.md
  最終報告書の章立てテンプレート
- 99_encoding_notes.txt
  文字化け防止ルール

## 推奨運用
1. ZIP を展開する
2. 02_codex_starter_prompt.txt を Codex に貼る
3. Codex が 01 以降の関連文書を読む
4. 調査 → 比較 → 推奨案 → 詳細設計 → DR → 実装 → テスト → 報告 の順で進める

## 備考
本パッケージは、プレス金型アプリについて
「厳密な FEM よりも、どのステージでどのように製品形状が変わるかを
ユーザーへ視覚的に伝えること」を重視しています。
また、将来の OpenRadioss / OpenFOAM 連携を前提に、拡張余地を残す方針です。
