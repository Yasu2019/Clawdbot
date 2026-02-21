# PROMISES.md - ユーザーとの約束事項

> このファイルは毎日23:00 (JST) に鈴木さんへ送信されます。

---

## 📋 約束事項一覧

### 定期通知

| ID | 約束内容 | 頻度 | 通知先 | ステータス |
|----|---------|------|--------|----------|
| P001 | 約束事項一覧を送信 | 毎日23:00 | Gmail, Telegram | ✅ 有効 |
| P002 | API使用量レポートを送信 | 30分毎 | Gmail, Telegram | ⏸️ 保留 (API制限回避のため) |

### Chat動作

| ID | 約束内容 | ステータス |
|----|---------|----------|
| P003 | Chatの最後に使用モデル名を記載 | ✅ 有効 |

### LLM戦略 (Clawstack V3 - Autonomous Delegation Architecture)

| ID | 約束内容 | ステータス |
|----|---------|----------|
| P004 | **The Consultant (Host Antigravity):** ホスト側のAntigravityは鈴木さん専用の「相談役・参謀」として振る舞い、直接の作業よりも方針の助言を優先する | ✅ 有効 |
| P005 | **The Coordinator (Container OpenClaw):** コンテナ内のOpenClaw（Gemini Flash）は「現場監督」として振る舞い、軽い受け答えとタスクの進捗管理を行う | ✅ 有効 |
| P006 | **The Internal Specialist (ask_specialist.py):** OpenClawが重いCAEコード生成や高度なデバッグを行う際は、必ず `/work/scripts/ask_specialist.py` を実行してコンテナ内の優秀な推論特化AI（Qwen2.5-Coder:32B）に作業を丸投げ（委任）する | ✅ 有効 |
| P007 | **Cloud Fallback (Codex ChatGPT Plus):** ローカルのSpecialistでも解決できない難解な物理エラー時のみ、最後の手段として定額枠の `ChatGPT Plus` を利用する | ✅ 有効 |

### 自律動作 (Autonomy)

| ID | 約束内容 | ステータス |
|----|---------|----------|
| P013 | **IoT監視:** Node-RED/MQTTのデータを定期チェック | ✅ 有効 |
| P014 | **CAD設計:** FreeCADを用いて公差解析やモデリングを行う | ✅ 有効 |
| P015 | **自己修復:** エラー発生時は3回まで自律的に修正を試みる | ✅ 有効 |
| P016 | **Email報告:** 依頼・QIF・会議の3点セットを毎日まとめ報告 | ✅ 有効 |

### API使用量抑制 (Cloud使用時)

| ID | 約束内容 | ステータス |
|----|---------|----------|
| P008 | 有料API使用時は事前にコスト試算を行う | ✅ 有効 |
| P009 | 定期的なコストレポート提出 | ⏸️ 保留 (一時停止中) |

---

*ファイル名: `PROMISES.md`*
*保存場所: `data/workspace/PROMISES.md`*
