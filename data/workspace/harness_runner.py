#!/usr/bin/env python3
"""
Harness Runner — Planner → Executor → Critic → Gate ループ
Harness Protocol (data/workspace/AGENTS.md 付属ファイル群) に基づく。

使い方:
  python3 /home/node/clawd/harness_runner.py "タスク説明文"
  python3 /home/node/clawd/harness_runner.py "タスク説明文" --max-retry 5
  python3 /home/node/clawd/harness_runner.py "タスク説明文" --json

設定:
  LITELLM_BASE = http://litellm:4000/v1  (Docker 内部)
  モデルは ROLE_MODELS で変更可
"""

import argparse, json, os, sys, time
from datetime import datetime, timezone
import requests

# ── 設定 ───────────────────────────────────────────────────
LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://litellm:4000/v1")
LITELLM_KEY  = os.environ.get("LITELLM_KEY",  "local-dev-key")
OLLAMA_BASE  = os.environ.get("OLLAMA_BASE",  "http://ollama:11434")

ROLE_MODELS = {
    "planner":  os.environ.get("PLANNER_MODEL",  "google/gemini-2.5-flash"),
    "executor": os.environ.get("EXECUTOR_MODEL", "ollama/qwen2.5-coder:7b"),
    "critic":   os.environ.get("CRITIC_MODEL",   "ollama/deepseek-r1:14b"),
}

MAX_RETRY_DEFAULT = 3
GATE_PASS_SCORE   = 80   # Critic が返すスコアの合格ライン (0-100)
TIMEOUT_SECS      = 120

# ── LiteLLM 呼び出し ────────────────────────────────────────
def call_llm(role: str, messages: list[dict], temperature: float = 0.3) -> str:
    model = ROLE_MODELS[role]
    url   = f"{LITELLM_BASE}/chat/completions"
    body  = {
        "model":       model,
        "messages":    messages,
        "temperature": temperature,
        "max_tokens":  2048,
    }
    try:
        r = requests.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {LITELLM_KEY}",
                     "Content-Type":  "application/json"},
            timeout=TIMEOUT_SECS,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        # LiteLLM 未起動 → Ollama 直接フォールバック
        return call_ollama_fallback(role, messages)
    except Exception as e:
        return f"[ERROR] {role} LLM呼び出し失敗: {e}"


def call_ollama_fallback(role: str, messages: list[dict]) -> str:
    """LiteLLM が使えない場合、Ollama に直接問い合わせる"""
    model_map = {
        "planner":  "qwen2.5-coder:7b",
        "executor": "qwen2.5-coder:7b",
        "critic":   "deepseek-r1:14b",
    }
    model = model_map.get(role, "qwen2.5-coder:7b")
    prompt = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in messages
    )
    body = {"model": model, "prompt": prompt, "stream": False}
    try:
        r = requests.post(f"{OLLAMA_BASE}/api/generate", json=body, timeout=TIMEOUT_SECS)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        return f"[FALLBACK ERROR] {e}"


# ── 各エージェントの実装 ────────────────────────────────────

def planner(task: str) -> dict:
    """タスクを分解してステップ計画を返す"""
    system = (
        "あなたはタスク計画エージェントです。\n"
        "ユーザーのタスクを具体的なステップに分解し、JSON で返してください。\n"
        "形式: {\"steps\": [\"step1\", \"step2\", ...], \"approach\": \"概要説明\", "
        "\"risks\": [\"リスク1\", ...]}"
    )
    messages = [
        {"role": "system",  "content": system},
        {"role": "user",    "content": f"タスク: {task}"},
    ]
    raw = call_llm("planner", messages, temperature=0.2)

    # JSON抽出試行
    try:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except json.JSONDecodeError:
        pass

    return {"steps": [raw], "approach": raw, "risks": []}


def executor(task: str, plan: dict, retry_feedback: str = "") -> str:
    """計画に基づいてタスクを実行し、結果テキストを返す"""
    steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(plan.get("steps", [])))
    feedback_section = f"\n前回の批評: {retry_feedback}" if retry_feedback else ""

    system = (
        "あなたは実行エージェントです。\n"
        "与えられた計画に従ってタスクを実行し、結果・成果物・手順を詳細に説明してください。\n"
        "実際のコマンドやコードが必要な場合は具体的に記述してください。"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": (
            f"タスク: {task}\n\n"
            f"実行計画:\n{steps_text}\n"
            f"アプローチ: {plan.get('approach', '')}{feedback_section}\n\n"
            "タスクを実行し、結果を報告してください。"
        )},
    ]
    return call_llm("executor", messages, temperature=0.3)


def critic(task: str, execution_result: str) -> dict:
    """実行結果を批評し、スコア(0-100)と改善点を返す"""
    system = (
        "あなたは厳格な批評エージェントです。\n"
        "実行結果を評価し、必ずJSON形式で返してください。\n"
        "形式: {\"score\": 0-100, \"passed\": true/false, "
        "\"strengths\": [\"良い点\"], \"improvements\": [\"改善点\"], \"summary\": \"総評\"}\n"
        f"合格ライン: score >= {GATE_PASS_SCORE}"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": (
            f"元のタスク: {task}\n\n"
            f"実行結果:\n{execution_result}\n\n"
            "この結果を厳格に評価してください。"
        )},
    ]
    raw = call_llm("critic", messages, temperature=0.1)

    try:
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
            # passed を score から自動算出（LLMが間違えた場合のガード）
            parsed["passed"] = parsed.get("score", 0) >= GATE_PASS_SCORE
            return parsed
    except json.JSONDecodeError:
        pass

    # パース失敗: スコア抽出を試みる
    import re
    m = re.search(r"score[\":\s]+(\d+)", raw, re.IGNORECASE)
    score = int(m.group(1)) if m else 0
    return {
        "score": score,
        "passed": score >= GATE_PASS_SCORE,
        "strengths": [],
        "improvements": [raw],
        "summary": raw[:200],
    }


# ── メインループ ────────────────────────────────────────────

def run_harness(task: str, max_retry: int = MAX_RETRY_DEFAULT) -> dict:
    started_at = datetime.now(timezone.utc).isoformat()
    log = []
    retry_feedback = ""

    print(f"\n{'='*60}")
    print(f"Harness Runner — タスク: {task[:80]}")
    print(f"{'='*60}")
    print(f"モデル: Planner={ROLE_MODELS['planner']} / Executor={ROLE_MODELS['executor']} / Critic={ROLE_MODELS['critic']}")
    print(f"最大リトライ: {max_retry}  合格スコア: {GATE_PASS_SCORE}")

    # Step 1: Plan
    print(f"\n[1/3] Planner 起動...")
    plan = planner(task)
    steps = plan.get("steps", [])
    print(f"  計画: {plan.get('approach', '')[:100]}")
    for i, s in enumerate(steps[:5]):
        print(f"  step{i+1}: {s[:80]}")

    # Retry loop
    for attempt in range(1, max_retry + 1):
        print(f"\n[2/3] Executor 起動 (試行 {attempt}/{max_retry})...")
        result = executor(task, plan, retry_feedback)
        print(f"  結果 ({len(result)}文字):\n  {result[:200]}{'...' if len(result) > 200 else ''}")

        print(f"\n[3/3] Critic 評価 (試行 {attempt}/{max_retry})...")
        evaluation = critic(task, result)
        score   = evaluation.get("score", 0)
        passed  = evaluation.get("passed", False)
        summary = evaluation.get("summary", "")

        log.append({
            "attempt":    attempt,
            "score":      score,
            "passed":     passed,
            "result_len": len(result),
            "summary":    summary,
        })

        print(f"  スコア: {score}/100  {'✅ 合格' if passed else '❌ 不合格'}")
        print(f"  総評: {summary[:150]}")

        if evaluation.get("improvements"):
            print(f"  改善点: {evaluation['improvements'][0][:100]}")

        if passed:
            print(f"\n{'='*60}")
            print(f"✅ 完了 (試行{attempt}回, スコア{score})")
            print(f"{'='*60}")
            return {
                "status":     "passed",
                "task":       task,
                "attempts":   attempt,
                "final_score": score,
                "plan":       plan,
                "result":     result,
                "evaluation": evaluation,
                "log":        log,
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }

        # Gate 不合格 → フィードバックを渡して再試行
        improvements = evaluation.get("improvements", [])
        retry_feedback = "; ".join(improvements[:3]) if improvements else summary

        if attempt < max_retry:
            print(f"  → リトライ準備中... フィードバック: {retry_feedback[:100]}")
            time.sleep(2)

    # 全試行失敗
    best_attempt = max(log, key=lambda x: x["score"], default={})
    print(f"\n{'='*60}")
    print(f"❌ 最大試行数到達 ({max_retry}回). 最高スコア: {best_attempt.get('score', 0)}")
    print(f"{'='*60}")
    return {
        "status":     "failed",
        "task":       task,
        "attempts":   max_retry,
        "final_score": best_attempt.get("score", 0),
        "plan":       plan,
        "result":     "",
        "evaluation": {},
        "log":        log,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }


# ── CLI エントリポイント ────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Harness Runner: Planner→Executor→Critic")
    parser.add_argument("task",        help="実行するタスクの説明")
    parser.add_argument("--max-retry", type=int, default=MAX_RETRY_DEFAULT,
                        help=f"最大リトライ数 (default: {MAX_RETRY_DEFAULT})")
    parser.add_argument("--json",      action="store_true",
                        help="結果をJSON形式で出力")
    args = parser.parse_args()

    result = run_harness(args.task, max_retry=args.max_retry)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = result["status"]
        print(f"\n--- 最終結果 ---")
        print(f"ステータス: {status.upper()}")
        print(f"試行回数: {result['attempts']}")
        print(f"最終スコア: {result['final_score']}/100")
        if result.get("result"):
            print(f"\n実行結果:\n{result['result'][:500]}")


if __name__ == "__main__":
    main()
