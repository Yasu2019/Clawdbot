# Clawstack フリート稼働状況レポート
**生成日時:** 2026-06-14  
**生成元:** K10 (NucBox K10 / 100.119.18.40)  
**参照元:** fleet_diagnostics_status.json / growth_dashboard / portal / INCIDENT_LOG

---

## 1. フリートノード現況

| ノード | Tailscale IP | ステータス | CPU | RAM | 温度 | 役割 |
|---|---|---|---|---|---|---|
| **K10** | 100.119.18.40 | ✅ ONLINE | 29% | 44% | 27.9°C (fallback) | メイン統括・オーケストレーション |
| **Red LAVIE** | 100.99.145.3 | ✅ ONLINE | 56% | 33% | 45.0°C (LHM) | CAEオフロード・中〜重タスク |
| **LAVIE** | 100.87.244.46 | ✅ ONLINE | 0% | 65% | 57.9°C (fallback) | CAEワーカー（OpenFOAM/OpenRadioss） |
| **Vivobook mhn15** | 100.65.182.27 | ✅ ONLINE | 27% | 51% | 52.0°C (LHM) | 軽タスク専用（昼間は業務PC） |
| **Dynabook** | 100.98.133.40 | ✅ ONLINE | 4% | 40% | 72.0°C (LHM) | 軽監視・小ジョブ（温度高め注意） |
| **G3** | 100.121.241.128 | ✅ ONLINE | - | - | - | n8n自動化・スクレイピング |
| **ThinkPad L590** | 100.66.63.9 | ❌ OFFLINE | - | - | - | SSH接続タイムアウト中 |
| **Lavie Core i3** | 100.67.36.121 | ⏳ PENDING | - | - | - | 新規追加・monitor_agent未起動 |

> **Dynabook 注意:** 温度72°C → 熱的マージン薄い。重タスク禁止。  
> **ThinkPad:** SSH疎通なし（2026-06-15 18:33時点）。原因調査が必要。  
> **Lavie Core i3:** 本日フリート登録完了。Python/monitor_agent導入待ち。

---

## 2. K10 稼働中サービス

### 常時稼働プロセス（K10ローカル）

| サービス | 状態 | 詳細 |
|---|---|---|
| Email Watchdog | ✅ 正常 | 最終更新 1分前・Gmail ingest継続中 (14,880件) |
| Docker Desktop UI Watchdog | ✅ 正常 | healthy |
| n8n 自動化エンジン | ✅ 正常 | http://127.0.0.1:5679 / WF 16本稼働 |
| Claudian Watchdog | ✅ 正常 | healthy |
| Mini PC Optimizer | ✅ 正常 | healthy |
| Auto Repair Patrol | ✅ 正常 | 最終実行 54分前 |
| Risk Notification Patrol | ✅ 正常 | 最終実行 54分前 |
| RAG Vector DB (Qdrant) | ✅ 正常 | 16コレクション / http://localhost:8110 |
| OpenClaw Gateway | ✅ 稼働 | port 18789/18791 |
| Email Blacklist Hub | ✅ 稼働 | blacklist=130件, candidates=120件 |
| **Paperless NGX** | ❌ 停止 | port 8000 接続拒否 → 要再起動 |

---

## 3. 知識獲得状況（RAG / Qdrant）

**総知識量:** growth_stats.json より（2026-06-15 18:00時点）

| ドメイン | 蓄積件数 |
|---|---|
| CAE_MATERIAL（CAE・材料・充填） | **3,325件** |
| SCRIBD_DOCUMENT（技術文書） | **2,975件** |
| GMAIL_READING（メール情報） | 450件 |
| IATF_AUDITING_YT（YouTube解析） | 348件 |
| IE（生産工学） | 307件 |
| QUALITY（品質管理） | 152件 |
| TERMINOLOGY（専門用語） | 151件 |
| CAD（DXF/STEP） | 132件 |
| MUSIC / MUSIC_THEORY | 123 / 95件 |
| GEOMETRY_AI | 127件 |
| TOLERANCE_ANALYSIS | 48件 |
| DXF2STEP | 15件 |
| 3D_ANIMATION | 249件 |

**直近30日学習トレンド:** 5月後半〜6月初旬にかけてピーク（最大944件/日: 2026-06-06）  
現在は 183〜306件/日 で安定推移。

---

## 4. IATF内部監査動画 生成状況

**完成本数:** 42本（`_slide_reviewed.mp4`）

### 主な完成動画（箇条別）
- 箇条4.4.1 品質マネジメントシステム
- 箇条6.2 品質目標
- 箇条7.1.3.1 インフラストラクチャ
- 箇条7.1.5.1.1 測定システム解析（MSA）× 複数本
- 箇条7.2.2 力量・OJT・製造工程監査
- 箇条8.2.3.1.3 製造フィージビリティ
- 箇条8.3.4.4 製品承認プロセス（PPAP）
- 箇条8.4.1 外部提供プロセス管理
- 箇条8.5.1.2〜8.5.6 生産管理全般
- 箇条8.6 製品リリース・最終検査
- 箇条8.7.1.7 不適合製品管理
- 箇条9.1.1.1〜9.1.1.3 監視・測定・統計
- 箇条9.3 マネジメントレビュー
- 箇条10 改善・ポカヨケ

### YouTube解析状況
- 対象動画: 349本 / 分析完了: **347本（99.4%）**
- 未分析: 3本（トランスクリプト無効）

---

## 5. システム正常性チェック（本日）

| 項目 | 状態 |
|---|---|
| Email 締切検出率 | 74.3%（目標: 80%以上）← 要改善 |
| Outbound送信ガード | ✅ 有効（Gmail: y.suzuki.hk@gmail.com / Telegram: 8173025084 / blocked=0） |
| Email安全ポリシー | ✅ draft_only=true, auto_send=false |
| API コスト | ✅ 実費 0円（無料枠 + ローカルLLM中心） |
| Git push 状態 | ✅ リモート同期済み |

---

## 6. 進行中・要確認事項

| 優先度 | 項目 | 状態 |
|---|---|---|
| 🔴 高 | **Paperless NGX 停止**（port 8000拒否） | → `docker start paperless` or compose up |
| 🔴 高 | **ThinkPad SSH接続タイムアウト** | → 電源・Tailscale確認が必要 |
| 🟡 中 | **Dynabook 温度72°C** | → 重タスク禁止継続。冷却改善推奨 |
| 🟡 中 | **LAVIE temp_source=fallback**（LHM未設定） | → `lhm_setup.ps1` 実行で修正可 |
| 🟡 中 | **K10 temp_source=fallback** | → LHM HTTP設定が必要 |
| 🟡 中 | **Email締切検出率 74.3%**（目標未達） | → quality_eval再実行で改善 |
| 🟢 低 | **Lavie Core i3 monitor_agent未起動** | → Python + monitor_agent インストール待ち |
| 🟢 低 | **箇条8.5.1.5 IATF動画** | → LLM API復旧後に run_host.py 再実行 |

---

## 7. 最近のインシデント（抜粋）

| ID | 日付 | 概要 | 解決 |
|---|---|---|---|
| INC-112 | 2026-06-10 | フリート診断エージェントの部分的盲点（旧monitor_agent） | ✅ fleet_diagnostics_audit.py 導入 |
| INC-111 | 2026-06-10 | LAVIE 温度表示「要LHM」（LHMサーバー未起動） | ✅ lhm_setup.ps1 更新（要手動実行） |
| INC-110 | 2026-06-10 | ThinkPad 24x7ジョブループ未構築 | ✅ k10_thinkpad_continuous_loop.py 追加 |
| INC-093 | 2026-05-23 | UE5 EXR→PNG変換未対応でOpenVINO HTTP500 | ✅ バイナリ署名チェック + ffmpeg変換を追加 |

---

## 8. アーキテクチャ概要

```
K10 (統括・オーケストレーション)
├── Docker (LiteLLM / Qdrant / n8n / OpenClaw Gateway / Paperless)
├── フリート監視 (fleet_diagnostics_audit.py / monitor_agent :8111)
├── IATF動画生成パイプライン (run_host.py → slides → mp4)
├── Email自律処理 (watchdog + blacklist + RAG ingest)
│
├─── Red LAVIE (100.99.145.3) ← CAEオフロード・IATF品質
├─── LAVIE (100.87.244.46)    ← OpenFOAM / OpenRadioss
├─── Dynabook (100.98.133.40) ← 軽ジョブ
├─── Vivobook (100.65.182.27) ← 軽ジョブ（昼間制限）
├─── G3 (100.121.241.128)     ← n8n自動化・スクレイピング
├─── ThinkPad (100.66.63.9)   ← [OFFLINE] CAE候補
└─── Lavie Core i3 (100.67.36.121) ← [PENDING] 新規追加
```

---

*このレポートは K10 上のデータから自動収集・生成されました。*  
*出典: fleet_diagnostics_status.json / growth_stats.json / continuous_system_improvement_summary.md / INCIDENT_LOG.md / portal.html / growth_dashboard*
