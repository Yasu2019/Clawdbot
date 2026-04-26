# 01_IMPLEMENTATION_PROTOCOL_ja

## 1. 前提
- Docker / Docker Compose が使えること
- Ollama がローカルで起動できること
- 診断対象は**自社管理下**または**明示許可済み**であること
- 本番ではなく、まずは検証用レプリカ環境から始めること

## 2. 導入の順序
### Step A. 構成ファイルの確認
1. `configs/.env.example` を `.env` にコピー
2. Ollama の URL、モデル名、対象パスを編集
3. `ALLOWED_TARGETS` に許可済みホストだけを入れる

### Step B. コンテナ起動
```bash
cd docker
docker compose up -d
```

### Step C. 静的解析を先に実施
```bash
bash ../scripts/run_static_scan.sh
```

### Step D. 動的確認（検証環境のみ）
```bash
bash ../scripts/run_zap_baseline.sh
```

### Step E. AIレビューと報告書化
- Clearwing または別のローカルLLMに、
  - Semgrep結果
  - Bandit結果
  - ZAP結果
  - 重要ファイル一覧
  を渡し、再現性と優先順位を要約させる

## 3. 推奨の進め方
- 最初は read-only 観点を徹底
- 危険コマンドは禁止
- 修正案は必ず別ブランチ
- 報告書は `templates/report_template.md` を基に残す

## 4. 将来拡張
- n8n で nightly scan 化
- OpenClaw でトリアージ支援
- Qdrant へ結果蓄積して類似脆弱性検索
