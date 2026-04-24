# Hybrid Eval Harness（Ollama 主系 + Foundry 比較系）

このツールは「主系は Ollama のまま」「Foundry は比較用に任意で併用」という運用を、**read-only / 観測のみ**で回せるようにするための最小ハーネスです。

## 使い方（Ollama のみ）
```powershell
python scripts/hybrid_eval/hybrid_eval.py --ollama-model qwen2.5-coder:7b --prompt-file .\\your_prompt.txt
```

### 生成量を制限（推奨）
タイムアウトしやすい場合は `--num-predict`（最大生成トークン）を付けます。
```powershell
python scripts/hybrid_eval/hybrid_eval.py --ollama-model qwen2.5-coder:7b --num-predict 256 --prompt-file .\\your_prompt.txt
```

## 使い方（Foundry 併用）
Foundry 側は「標準入力に prompt を受け取り、標準出力に結果を出す」任意コマンドを指定します。

```powershell
python scripts/hybrid_eval/hybrid_eval.py `
  --ollama-model qwen2.5-coder:7b `
  --prompt-file .\\your_prompt.txt `
  --foundry-cmd python .\\scripts\\hybrid_eval\\foundry_openai_compat.py --base-url http://127.0.0.1:8000/v1 --model <FOUNDY_MODEL_ID>
```

### Foundry エンドポイント探索（任意）
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/hybrid_eval/discover_foundry_endpoint.ps1
```

## 出力
- `tmp/hybrid_eval/<run_id>/input_prompt.txt`
- `tmp/hybrid_eval/<run_id>/run_meta.json`
- `tmp/hybrid_eval/<run_id>/ollama_raw.json`
- `tmp/hybrid_eval/<run_id>/foundry_raw.json`
- `tmp/hybrid_eval/<run_id>/comparison.md`（人手評価のメモ用）

## ロールバック
- Foundry 併用を止める: `--foundry-cmd` を外すだけ（Ollama 単独で動作）
