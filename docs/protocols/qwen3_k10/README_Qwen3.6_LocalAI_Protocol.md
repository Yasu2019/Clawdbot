# Qwen3.6-35B-A3B 本気版プロトコル（GMKtec K10 / Windows 11 / Ollama 想定）

対象:
- PC: GMKtec K10
- CPU: Intel Core i9-13900HK
- RAM: 48GB
- OS: Windows 11 Pro
- 目的: 機密をクラウドに出さずに、ローカルAIを実務利用する
- 優先モデル: Qwen系（Qwen3.6 / Qwen3 / Qwen2.5-Coder など）
- 実行基盤: Ollama
- 想定連携: Codex CLI / Claude Code / Antigravity / OpenClaw / LiteLLM / Qdrant / n8n

---
## 1. 結論

Qwen3.6-35B-A3B は「ローカルでかなり強い」ですが、GPUなしのK10では常用主力にするより、
以下の二段構えが実務的です。

- 日常主力:
  - qwen3:14b
  - qwen2.5-coder:14b
- 重い解析・長文レビュー:
  - qwen3.6:35b-a3b

理由:
- Qwen3.6-35B-A3B は高性能だが、4bit量子化でも大きい
- CPUのみだと動作は可能でも遅くなりやすい
- 48GB RAM は「載る可能性が高い」容量だが、快適さは別問題
- 実務では「軽量主力 + 重量級スポット起用」が最も安定する

---
## 2. 最新確認済みの要点

- Ollamaの qwen3.6:35b-a3b は公開済み
- Ollama上の標準タグは Q4_K_M / 約24GB 表記
- ライセンスは Apache 2.0
- “agentic coding” と “thinking preservation” が主な訴求点
- Hugging Face上でも Qwen/Qwen3.6-35B-A3B が公開されている
- 長文処理は 262,144 トークン級として案内されている
- vLLM等では reasoning parser の注意点がある

---
## 3. あなたの環境での推奨方針

### A. GPUなし（現状）
推奨:
1. qwen3:14b を通常作業の主力にする
2. qwen2.5-coder:14b をコード専用で併用する
3. qwen3.6:35b-a3b は必要時のみ使う
4. コンテキスト長は欲張らず 16k〜64k から始める
5. RAGを併用して、毎回巨大コンテキストを流し込まない

### B. 将来GPU追加時
推奨:
- 12GB級以上のGPUが入れば、Qwen3.6系の実用度が一気に上がる
- OCuLink/eGPUを導入する場合は、まず qwen3:14b / qwen3.6 を比較し、
  速度・安定性・発熱・電力を測定する

---
## 4. 使い分けルール（重要）

### 普段の問い合わせ
- 監査文章の要約
- メール下書き
- VBA・Python修正
- 簡易コードレビュー
=> qwen3:14b か qwen2.5-coder:14b

### 重い問い合わせ
- 仕様書/図面説明文/議事録の長文横断
- 複数ソースコードの広域修正
- エージェント型の段取り作成
=> qwen3.6:35b-a3b

### 機密の高い問い合わせ
- 顧客不良情報
- IATF監査内部情報
- 生産条件・品質履歴
=> 必ずローカルモデル優先

---
## 5. Ollama導入（Windows）

1. Ollamaを導入
2. PowerShellで確認
   ollama --version

3. 軽量主力モデル導入
   ollama pull qwen3:14b
   ollama pull qwen2.5-coder:14b

4. 重量級モデル導入
   ollama pull qwen3.6:35b-a3b

5. 動作確認
   ollama run qwen3:14b
   ollama run qwen3.6:35b-a3b

---
## 6. 現実的な運用順序

### 第1段階
- qwen3:14b を導入
- 速度・安定性確認
- 日常用途に使えるか確認

### 第2段階
- qwen2.5-coder:14b を導入
- コード生成・修正・VBA変換で比較

### 第3段階
- qwen3.6:35b-a3b を導入
- 大きい文書・難しいコード修正時だけ使う

### 第4段階
- LiteLLM / Open WebUI / OpenClaw / n8n と連携

---
## 7. 実務向けのモデル選択指針

### 文書系
- 議事録整形
- QA文書レビュー
- 監査質問案
=> qwen3:14b

### コード系
- Python
- VBA
- Docker Compose
- PowerShell
=> qwen2.5-coder:14b
補助で qwen3.6

### 長文解析系
- IATF関連一式
- 規定・票・監査記録の横断読解
- 複数ファイルの整合確認
=> qwen3.6:35b-a3b

---
## 8. よくある失敗

1. 最初から最重量モデルだけで回そうとする
2. コンテキスト長を最初から最大近くにする
3. RAGなしで巨大資料を毎回丸投げする
4. エージェント化を急ぎすぎる
5. CPU推論なのにクラウド旗艦級の速度を期待する

---
## 9. 実務での安全ルール

- 社外秘はローカル限定
- モデル切替は用途別
- 外部送信する前に人間が確認
- 自動実行系は dry-run を必ず用意
- ファイル削除や書換はバックアップ後に実施

---
## 10. 一番おすすめの形

### いま
- Ollama
- qwen3:14b
- qwen2.5-coder:14b
- qwen3.6:35b-a3b（必要時のみ）

### 次
- LiteLLM
- Qdrant
- Open WebUI もしくは OpenClaw
- n8n

### 将来
- eGPU / OCuLink 導入
- モデル自動切替
- RAG込みの半自動品質支援エージェント化

---
## 11. あなた向け最終判断

「Qwen3.6を主力にして全部解決」ではなく、
「Qwen3.6を重量級カードとして持ち、軽量Qwenを主力にする」
のが最も賢いです。
