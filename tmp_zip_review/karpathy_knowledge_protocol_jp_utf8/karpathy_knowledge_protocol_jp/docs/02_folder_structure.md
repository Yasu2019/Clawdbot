# 02 Folder Structure

## 推奨ディレクトリ構成
```text
KnowledgeVault/
├─ raw/
│  ├─ web/
│  ├─ pdf/
│  ├─ papers/
│  ├─ internal/
│  └─ images/
├─ processed/
│  ├─ summaries/
│  ├─ indexes/
│  ├─ entities/
│  └─ relations/
├─ wiki/
│  ├─ topics/
│  ├─ qa/
│  ├─ projects/
│  ├─ glossary/
│  └─ decision_logs/
├─ inbox/
├─ archive/
├─ prompts/
├─ scripts/
└─ config/
```

## 各フォルダの役割
### raw/
未加工の原文書を置く場所です。PDF、記事保存、社内資料、画像OCR結果などを格納します。

### processed/
Claude Code や補助スクリプトにより加工された中間成果物を置きます。

### wiki/
最終的に人間が読む知識ベース本体です。Obsidianで主に開く想定です。

### inbox/
一時置き場です。後で raw へ移動する前の仮置きにも使えます。

### archive/
古い版や不要になった派生物を退避します。

## 運用原則
- raw は原本扱いで極力改変しない
- processed は再生成可能であるべき
- wiki は人間が育てる資産
- ファイル名は英数字とアンダースコア中心
