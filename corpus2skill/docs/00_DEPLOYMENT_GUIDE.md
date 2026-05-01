# 00 導入ガイド

## 目的
このパッケージは、既存の Clawstack / OpenClaw / Paperless / Qdrant / Langfuse 環境を壊さずに、Corpus2Skill 型の「構造探索RAG」を追加するための設計・実装テンプレートです。

## 推奨導入モード
最初は `read-only / shadow mode` で導入してください。

- 既存Qdrantコレクションは読み取りのみ
- Paperless文書も読み取りのみ
- Corpus2Skill側に生成される tree/evidence/navigation log のみ新規保存
- 既存Portalにはカード追加のみ

## 導入ステップ

### 1. バックアップ
Codex / Claude / OpenCode GO に依頼する前に、必ずGitHubまたはローカルGitでバックアップします。

```bash
cd /path/to/clawstack-unified
git status
git add .
git commit -m "backup before corpus2skill integration"
```

### 2. override compose追加
```bash
docker compose -f docker-compose.yml -f docker-compose.override.corpus2skill.yml up -d
```

### 3. ヘルスチェック
```bash
bash scripts/smoke_test.sh
```

### 4. 最初に入れる文書
優先順:
1. IATF 16949 関連文書
2. 社内品質マニュアル
3. QC工程表
4. 作業標準書
5. 図面PDF
6. STEP/STL/3Dモデルのメタ情報
7. 過去不具合・是正処置報告書

## 絶対に避けること
- 初回から全ファイル一括処理しない
- 既存Qdrantコレクションを上書きしない
- Paperlessの原文を改変しない
- AIに勝手な分類名を無制限に作らせない
- 根拠IDなしの回答を本番利用しない

