# Karpathy式ナレッジ構築プロトコル（文字化けしにくいUTF-8版）

本ZIPは、**Obsidian + Claude Code + 既存RAG（Paperless / Qdrant / Ollama 等）**を併用し、
自分専用Wikiを育てるための実務向けプロトコルです。

## このZIPの目的
- 生資料を集める
- Markdownへ整理する
- 質問と回答を蓄積する
- 矛盾や古さを保守する
- 将来的に自分専用の知識OSへ育てる

## 想定ユーザー
- Obsidianを使っている
- Claude Code を使える、または導入予定
- ローカル環境やRAGを既に持っている
- 技術資料、品質資料、監査資料、不具合情報、社内手順書を横断活用したい

## 文字化け対策
- すべて **UTF-8 / 改行LF** で保存
- Windowsでも開きやすいように、拡張子は主に `.md`, `.json`, `.txt`, `.yaml`, `.ps1`, `.bat`
- 日本語ファイル名は最小限に抑え、英数字中心
- パスは短めに設計

## 推奨配置
`D:\KnowledgeVault\` など、短い英数字パスに展開してください。

## 収録物
- `docs/` : 導入手順・運用手順
- `templates/` : Obsidian用テンプレート
- `prompts/` : Claude Codeへ渡すプロンプト
- `scripts/` : フォルダ作成や初期化の補助
- `examples/` : 実際のノート例
- `config/` : 運用ルール例

## 最初に読む順番
1. `docs/01_overview.md`
2. `docs/02_folder_structure.md`
3. `docs/03_ingest_compile_query_maintain.md`
4. `docs/04_claude_code_protocol.md`
5. `docs/05_obsidian_operation.md`

## 注意
このZIPは**実装候補のたたき台**です。  
導入・不導入の最終判断は、受け取る側の **Codex / Claude / 社内レビュー** に委ねてください。
