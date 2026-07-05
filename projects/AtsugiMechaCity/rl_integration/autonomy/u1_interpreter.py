# -*- coding: utf-8 -*-
"""U1: 依頼解釈器(S2) — skill_pipeline_implementation_spec.md 準拠。

skill_requests.json の status=="queued" 行を解釈し、
interpretation {skill_name, taxonomy, required_tier, needs_terrain, search_keywords}
を追記して status="interpreted" にする。
一次: ローカルLLM(LiteLLM local_fast)。失敗時: キーワード対訳辞書フォールバック。
両方不能: status="needs_human_source"。

usage: python u1_interpreter.py --once
"""
import argparse, json, os, re, time, urllib.request

STORE = r"D:\Clawdbot_Docker_20260125\data\workspace\apps\mecha_motion_lab\skill_requests.json"
LITELLM = "http://localhost:4001/v1/chat/completions"
TAXONOMIES = ["locomotion", "posture", "manipulation", "care_assist",
              "factory_work", "most_basic", "therblig", "martial_arts", "sports"]
TERRAINS = [None, "stairs", "slope_up", "slope_down", "uneven"]

# フォールバック辞書(LLM不通時)。キー=依頼文の部分一致、値=interpretation
FALLBACK = [
    (("階段", "stairs"), {"skill_name": "stairs_climb", "taxonomy": "locomotion",
                          "required_tier": 1, "needs_terrain": "stairs"}),
    (("斜面を登", "坂を登", "slope up", "uphill"),
     {"skill_name": "slope_ascend", "taxonomy": "locomotion",
      "required_tier": 1, "needs_terrain": "slope_up"}),
    (("斜面を下", "坂を下", "slope down", "downhill"),
     {"skill_name": "slope_descend", "taxonomy": "locomotion",
      "required_tier": 1, "needs_terrain": "slope_down"}),
    (("歩く", "歩行", "walk"), {"skill_name": "walk", "taxonomy": "locomotion",
                                "required_tier": 1, "needs_terrain": None}),
    (("走る", "走行", "run"), {"skill_name": "run", "taxonomy": "locomotion",
                               "required_tier": 1, "needs_terrain": None}),
    (("立つ", "起立", "stand"), {"skill_name": "stand", "taxonomy": "posture",
                                 "required_tier": 1, "needs_terrain": None}),
    (("座る", "着座", "sit"), {"skill_name": "sit", "taxonomy": "posture",
                               "required_tier": 1, "needs_terrain": None}),
    (("持ち上げ", "つかむ", "掴む", "lift", "grasp", "pick"),
     {"skill_name": "lift_object", "taxonomy": "therblig",
      "required_tier": 2, "needs_terrain": None}),
    (("介助", "介護", "支え"), {"skill_name": "care_support", "taxonomy": "care_assist",
                                "required_tier": 2, "needs_terrain": None}),
    (("パンチ", "蹴り", "格闘"), {"skill_name": "martial_basic", "taxonomy": "martial_arts",
                                  "required_tier": 2, "needs_terrain": None}),
]

RUBRIC = (
    "You classify a motion-learning request for a bipedal mecha robot. "
    "Reply ONLY a JSON object: {\"skill_name\": snake_case_english, "
    "\"taxonomy\": one of " + str(TAXONOMIES) + ", "
    "\"required_tier\": 1|2|3 (1=locomotion/posture, 2=hands/objects, 3=fingers), "
    "\"needs_terrain\": null|\"stairs\"|\"slope_up\"|\"slope_down\"|\"uneven\", "
    "\"search_keywords\": [up to 4 english keywords]}. Request: "
)


def llm_interpret(text):
    body = json.dumps({"model": "local_fast", "max_tokens": 200,
                       "messages": [{"role": "user", "content": RUBRIC + text}]}).encode()
    req = urllib.request.Request(LITELLM, data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        content = json.load(r)["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", content, re.S)
    d = json.loads(m.group(0))
    # 妥当性検証(語彙外はフォールバックへ回すため例外)
    assert d.get("taxonomy") in TAXONOMIES, "bad taxonomy"
    assert d.get("required_tier") in (1, 2, 3), "bad tier"
    assert d.get("needs_terrain") in TERRAINS, "bad terrain"
    assert re.match(r"^[a-z0-9_]+$", str(d.get("skill_name", ""))), "bad skill_name"
    d.setdefault("search_keywords", [])
    d["source"] = "local_llm"
    return d


def fallback_interpret(text):
    for keys, base in FALLBACK:
        if any(k.lower() in text.lower() for k in keys):
            d = dict(base)
            d["search_keywords"] = [d["skill_name"].replace("_", " ")]
            d["source"] = "fallback_dictionary"
            return d
    return None


def interpret(text):
    # 既知ケースは辞書を最優先(精度が確実)。LLMは辞書に無い長尾ケースのみ。
    # 実測根拠: qwen3:8bが「走る」をwalkと誤分類(2026-07-05)。
    d = fallback_interpret(text)
    if d is not None:
        return d
    try:
        return llm_interpret(text)
    except Exception:
        return None


def run_once():
    if not os.path.exists(STORE):
        print("no queue file"); return 0
    data = json.load(open(STORE, encoding="utf-8"))
    changed = 0
    for req in data.get("requests", []):
        if req.get("status") != "queued":
            continue
        d = interpret(req["text"])
        if d is None:
            req["status"] = "needs_human_source"
            req["notes"] = "U1: LLMとフォールバック辞書の両方で分類不能"
        else:
            req["interpretation"] = d
            req["status"] = "interpreted"
        req["interpreted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        changed += 1
        print(f"U1 {req['id']}: '{req['text'][:30]}' -> {req['status']} "
              f"{json.dumps(d, ensure_ascii=False) if d else ''}")
    if changed:
        with open(STORE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"U1 done: {changed} request(s) processed")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.parse_args()
    raise SystemExit(run_once())
