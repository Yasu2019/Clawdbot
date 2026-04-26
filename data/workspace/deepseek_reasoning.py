#!/usr/bin/env python3
"""
DeepSeek-R1 推論サブエージェント
Tool非対応だが深い推論・思考が得意なdeepseek-r1:14bを
推論専用エンジンとして活用する。

使い方:
  python3 deepseek_reasoning.py "なぜQdrantのベクトル検索は高速なのか？"
  python3 deepseek_reasoning.py --model deepseek-r1:7b "問題文"
  echo "問題文" | python3 deepseek_reasoning.py -

用途:
  - 複雑な技術的推論（アーキテクチャ設計、障害分析）
  - 数学/論理問題
  - ステップバイステップの計画立案
  - gemini-2.5-flashで判断が難しい際のセカンドオピニオン
"""
import sys, json, urllib.request, argparse, time

OLLAMA_URL = "http://ollama:11434"  # Docker内部。ホストからは http://localhost:11434
DEFAULT_MODEL = "deepseek-r1:14b"


def check_model_available(model: str) -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        models = [m["name"] for m in data.get("models", [])]
        return any(m.startswith(model.split(":")[0]) for m in models)
    except:
        return False


def reason(problem: str, model: str = DEFAULT_MODEL,
           system_prompt: str = "", stream: bool = True) -> str:
    """deepseek-r1に推論を依頼し、思考過程と回答を返す"""

    if not system_prompt:
        system_prompt = (
            "あなたは深い推論が得意な技術アナリストです。"
            "問題を段階的に分析し、根拠を示しながら結論を導いてください。"
            "日本語で回答してください。"
        )

    payload = {
        "model": model,
        "prompt": problem,
        "system": system_prompt,
        "stream": stream,
        "options": {
            "temperature": 0.6,
            "num_predict": 4096,
        }
    }

    url = f"{OLLAMA_URL}/api/generate"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"}
    )

    full_response = ""
    thinking_text = ""
    in_thinking = False

    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            for line in r:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                token = chunk.get("response", "")
                full_response += token

                if stream:
                    # <think>タグの処理
                    if "<think>" in token:
                        in_thinking = True
                        print("\n[思考中...]", flush=True)
                    elif "</think>" in token:
                        in_thinking = False
                        print("\n[回答]", flush=True)
                    elif in_thinking:
                        print(token, end="", flush=True)
                    else:
                        print(token, end="", flush=True)

                if chunk.get("done"):
                    break
    except urllib.error.URLError as e:
        return f"エラー: Ollama接続失敗 ({e})\nホストから実行する場合は --url http://localhost:11434 を指定してください"
    except Exception as e:
        return f"エラー: {e}"

    return full_response


def extract_answer(response: str) -> tuple[str, str]:
    """<think>...</think> を思考部分と回答部分に分割"""
    import re
    think_match = re.search(r"<think>(.*?)</think>", response, re.DOTALL)
    thinking = think_match.group(1).strip() if think_match else ""
    answer = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
    return thinking, answer


def main():
    global OLLAMA_URL
    parser = argparse.ArgumentParser(description="DeepSeek-R1 Reasoning Subagent")
    parser.add_argument("problem", nargs="?", help="推論させる問題（'-'でstdin）")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"使用モデル (default: {DEFAULT_MODEL})")
    parser.add_argument("--url", default=OLLAMA_URL,
                        help=f"Ollama URL (default: {OLLAMA_URL})")
    parser.add_argument("--system", default="", help="システムプロンプト")
    parser.add_argument("--no-stream", action="store_true", help="ストリーミング無効")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    args = parser.parse_args()

    OLLAMA_URL = args.url

    if args.problem == "-":
        problem = sys.stdin.read().strip()
    elif args.problem:
        problem = args.problem
    else:
        parser.print_help()
        sys.exit(1)

    # モデル確認
    if not check_model_available(args.model):
        print(f"警告: {args.model} が見つかりません。利用可能なモデルを確認してください。")
        print(f"  docker exec clawstack-unified-ollama-1 ollama list")

    print(f"=== DeepSeek-R1 推論エンジン ({args.model}) ===")
    print(f"問題: {problem[:100]}...")
    print("=" * 50)

    start = time.time()
    response = reason(problem, args.model, args.system, stream=not args.no_stream)
    elapsed = time.time() - start

    if args.json:
        thinking, answer = extract_answer(response)
        print(json.dumps({
            "model": args.model,
            "problem": problem,
            "thinking": thinking,
            "answer": answer,
            "elapsed_sec": round(elapsed, 1),
        }, ensure_ascii=False, indent=2))
    elif args.no_stream:
        thinking, answer = extract_answer(response)
        if thinking:
            print(f"\n[思考プロセス]\n{thinking[:500]}...")
        print(f"\n[回答]\n{answer}")

    print(f"\n\n経過時間: {elapsed:.1f}秒")


if __name__ == "__main__":
    main()
