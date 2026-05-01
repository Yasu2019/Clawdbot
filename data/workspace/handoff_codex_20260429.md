# Codex 引き継ぎ資料 — 2026-04-29

> 作成者: Claude Sonnet 4.6 (Claude Code)
> 目的: セッション終了に伴い Codex (local qwen3:8b) に作業を引き継ぐ

**最初にすること**: 各セクションの「確認コマンド」を実行して現状を把握してから作業に入ること。

---

## 1. 現在稼働中のプロセス

### A. IATF動画生成 — Blender レンダリング

| 項目 | 値 |
|---|---|
| 進捗 | 20,239 / 24,960 フレーム (81%) |
| Blender PID | 30696 (Windows ホスト) |
| 出力先 | `d:/Clawdbot_Docker_20260125/data/iatf_videos/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ/frames/` |
| ログ | `d:/Clawdbot_Docker_20260125/data/iatf_videos/generation.log` |

**確認コマンド:**
```bash
# フレーム数確認
ls "d:/Clawdbot_Docker_20260125/data/iatf_videos/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ/frames/" | wc -l

# Blenderプロセス確認
tasklist | grep -i blender

# ログ末尾確認
tail -5 "d:/Clawdbot_Docker_20260125/data/iatf_videos/generation.log"
```

**Blender完了後の自動動作**: `run_host.py` が [6/6] FFmpeg MP4合成 + 字幕焼き込みを自動実行する。完了ログに `完了:` が出たら成功。

**MP4が生成されたか確認:**
```bash
ls "d:/Clawdbot_Docker_20260125/data/iatf_videos/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ/"*.mp4 2>/dev/null
```

---

### B. OpenRadioss Run35 — プレス金型シミュレーション

| 項目 | 値 |
|---|---|
| 状態 | 稼働中 (コンテナ内 PID は `/work/engine.pid` に記録) |
| 最終確認 | NC=2,000 / T=1.0E-04 / DM/M=7.02 / ERR≈0% |
| ログ | `d:/Clawdbot_Docker_20260125/clawstack_v2/data/work/engine_run35.log` |
| 問題 | 8秒/cycle (正常時は 0.1秒/cycle) — Blender完了後に速度回復するか要確認 |

**確認コマンド:**
```bash
# 最新進捗 (NC, T, DM/M, ELAPSED)
grep "NC=.*T=.*DT=\|ELAPSED" "d:/Clawdbot_Docker_20260125/clawstack_v2/data/work/engine_run35.log" | tail -6

# エンジンプロセス確認
docker exec clawstack-unified-openradioss-1 bash -c "for pid in \$(ls /proc | grep -E '^[0-9]+\$'); do cmd=\$(cat /proc/\$pid/cmdline 2>/dev/null | tr '\0' ' '); echo \"\$cmd\" | grep -q engine_linux64_gf && echo \"PID \$pid: running\"; done"

# 速度エラー・終了確認
grep "VELOCITY IS TOO HIGH\|NORMAL TERMINATION\|ERROR:" "d:/Clawdbot_Docker_20260125/clawstack_v2/data/work/engine_run35.log" | tail -5
```

**Blender完了後にすること:**
1. Run35 速度を確認 (sec/cycle が改善しているか)
2. 改善なければ → セクション4の「Run35 遅延対処」を参照

---

## 2. 重要操作ルール (必読)

### OpenRadioss エンジン操作

```bash
# ★ エンジン停止 (必ずこれを使う — pkill/SIGTERM は無効)
docker exec clawstack-unified-openradioss-1 bash -c "bash /work/kill_engine.sh"

# ★ エンジン起動 (既存エンジンを自動Kill後に起動)
docker exec clawstack-unified-openradioss-1 bash -c "bash /work/start_engine.sh <Run番号>"
# 例: bash /work/start_engine.sh 36
```

**⚠️ Windows Git Bash のパス変換に注意**: `/work/...` を直接渡すと `C:/Program Files/Git/work/...` に変換される。必ず `bash -c "bash /work/..."` 形式を使うこと。

### IATF動画パイプライン

```bash
# 通常起動 (resume機能あり: script.json+timeline.jsonが存在すればstep1-4をスキップ)
cd "d:/Clawdbot_Docker_20260125/clawstack_v2/apps/iatf_video_factory"
python run_host.py >> "d:/Clawdbot_Docker_20260125/data/iatf_videos/generation.log" 2>&1 &

# 特定PDFを指定する場合
python run_host.py --pdf "パス"
```

---

## 3. 主要ファイル一覧

| 目的 | パス |
|---|---|
| OpenRadioss モデル | `clawstack_v2/data/work/4mmx4mm_ASSY_20260105_0000.rad` |
| OpenRadioss エンジン制御 | `clawstack_v2/data/work/4mmx4mm_ASSY_20260105_0001.rad` |
| Run35 ログ | `clawstack_v2/data/work/engine_run35.log` |
| エンジン Kill スクリプト | `clawstack_v2/data/work/kill_engine.sh` |
| エンジン起動スクリプト | `clawstack_v2/data/work/start_engine.sh` |
| IATF動画パイプライン | `clawstack_v2/apps/iatf_video_factory/run_host.py` |
| 台本生成 | `clawstack_v2/apps/iatf_video_factory/pipeline/script_generator.py` |
| TTS | `clawstack_v2/apps/iatf_video_factory/pipeline/tts_renderer.py` |
| Blender アニメ | `clawstack_v2/apps/iatf_video_factory/pipeline/blender_animator.py` |
| 動画出力 | `data/iatf_videos/` |
| 過去トラブルログ | `data/workspace/memory/trouble_history.md` |
| 引き継ぎ履歴 | `data/workspace/handoff_codex_20260426.md` (前回) |

---

## 4. 待機中の判断事項

### A. Run35 完走が非現実的な場合の対処

Blender 完了後も Run35 が 8秒/cycle のままなら、以下を順に検討:

**Option 1: DT ターゲットを緩める (推奨)**

エンジンファイル `_0001.rad` を編集:
```
# 変更前
/DT/NODA/CST/0
             0.90000             0.50000E-07   ← target DT = 5E-8

# 変更後 (DT を 1E-7 に緩める → cycle数半減)
/DT/NODA/CST/0
             0.90000             0.10000E-06
```
変更後は Starter 再実行 → Engine 再起動が必要。

**Option 2: Run35 を終了して結果を分析**

Run33 (NORMAL TERMINATION, T=0.02745s, DM/M=12.5) の結果を使う。
物理的には疑問があるが変形パターンの定性分析には使える可能性がある。

### B. IATF動画 次のPDFを処理する

1本目 (箇条10.2.4ポカヨケ) の MP4 生成完了後、残り40本を処理する:
```bash
# 未処理PDF確認
ls "d:/Clawdbot_Docker_20260125/iatf_system/db/documents/"IATF*.pdf | wc -l

# 次の1本を処理 (limit=1)
cd "d:/Clawdbot_Docker_20260125/clawstack_v2/apps/iatf_video_factory"
python run_host.py --limit 1
```

---

## 5. 既知の問題・制約

| 問題 | 対処済み? | 詳細 |
|---|---|---|
| Docker ポートフォワーディング (4001) | ✅ 回避済み | `script_generator.py` に直接API フォールバック実装 (OpenCode GO / Gemini 直接呼び出し) |
| OpenRadioss ゾンビプロセス | ✅ 対策済み | `kill_engine.sh` を使うこと (T001参照) |
| Blender タイムアウト | ✅ 修正済み | `timeout=None` に変更済み |
| キャラ名不一致 (17gou/18gou) | ❌ 未修正 | Gemini が `android17`/`android18` の代わりに `17gou`/`18gou` を生成する。`tts_renderer.py` の SPEAKER_MAP に alias を追加すれば解消 |
| Run35 速度異常 | ❌ 要観察 | Blender完了後に速度確認。改善なければ DT 緩和 (セクション4-A) |

---

## 6. 環境情報

- **Docker**: `clawstack-unified` (docker-compose.yml)
- **LiteLLM**: port 4001 (ホスト→Docker フォワーディング障害中) / port 4000 (コンテナ内は正常)
- **VoiceVox**: `http://localhost:50021`
- **Blender**: `C:/Program Files/Blender Foundation/Blender 5.1/blender.exe`
- **OpenRadioss コンテナ**: `clawstack-unified-openradioss-1`
- **過去トラブル詳細**: `data/workspace/memory/trouble_history.md` (T001〜T004)
- **モデルルーティング**: 軽タスク→`local_fast`, 実装→`codex`, 通常→`google/gemini-2.5-flash`
