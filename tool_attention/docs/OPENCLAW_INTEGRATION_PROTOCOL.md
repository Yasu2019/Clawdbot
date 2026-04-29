# OpenClaw統合プロトコル

## 1. 既存処理の置換位置
OpenClawがLLMへツール一覧を渡す直前で、以下に置換します。

1. ユーザー指示 + 現在状態を `/route` に送る
2. selected上位ツールだけを取得
3. 各ツールの詳細schemaを `/schema/{tool}` から遅延取得
4. LLMに注入
5. 実行後に `/feedback` へ成功/失敗を返す

## 2. 疑似コード
```python
selected = post("http://tool-router:8090/route", {"text": user_text, "state": state})
for tool in selected["selected"]:
    schema = get(f"http://lazy-loader:8091/schema/{tool['name']}")
    prompt_tools.append(schema)
result = call_llm(user_text, prompt_tools)
post("http://tool-router:8090/feedback", {"tool": used_tool, "success": ok, "latency_ms": latency})
```

## 3. 状態stateの標準キー
- db_connected
- mqtt_connected
- nodered_connected
- paperless_connected
- github_connected
- write_allowed
- human_approved
- maintenance_mode

## 4. 現場安全ルール
- SQLはSELECTのみ
- GitHubバックアップなしの大規模変更は禁止
- write/dangerousは人間承認がない限り候補から除外
- 失敗率が高いツールはlearning-storeが自動的に順位を下げる
