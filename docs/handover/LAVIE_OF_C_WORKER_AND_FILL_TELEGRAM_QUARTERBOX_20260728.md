# Handover: Lavie OF C: worker + fill Telegram 1/4-box fix (2026-07-28)

## 0. 次セッションが最初にやること

1. `data/workspace/memory/trouble_history.md` **[T019]** と `docs/cae_north_star_and_meaning_gate_protocol.md` を確認
2. 本ファイルを読む（残作業は末尾）
3. Lavie ワーカーは **`:5683`（C:）** を使う。**`:5682`（E: stub）は禁止**

---

## 1. ゴール / コンテキスト

| 項目 | 内容 |
|---|---|
| 北極星 | プレス部品3D → Moldflow級キャビティ充填（VOF）→ 順送金型 |
| 本セッション | (1) Lavie OF 再開失敗の復旧 (2) 成功 trial の充填アニメを Telegram 送信 (3) 「箱の1/4しか見えない」可視化バグ修正 |

---

## 2. ホスト / 到達経路

| Host | Role | Reach |
|---|---|---|
| K10 | Orchestrator / Telegram render | 本リポ `D:\Clawdbot_Docker_20260125` |
| Lavie `100.87.244.46` | OpenFOAM VOF | Job worker **`http://100.87.244.46:5683`**, n8n exec_bridge `:5679` |
| Dynabook `100.98.133.40` | Moldflow（別スレ） | SSH `mec21` / key `~/.ssh/moldflow_remote_ed25519` |

レジストリ: `data/workspace/lavie_node_registry.json`  
ルーター: `data/workspace/cae_workload_router.yaml`（`job_worker_port: 5683`, `lavie_work_dir: C:/...`）

---

## 3. 障害と修正（Lavie ディスク / worker）

### 症状

- Meaning gate / empty JSON: `Expecting value: line 1 column 1`
- 根本: Lavie **E: ~798 MB stub** → `[Errno 28] No space left on device`
- Host worker `:5682` が E: を指したまま → n8n `/work` と Docker `c:/` キャッシュ不一致

### 対策（実施済み）

- Docker worker **`lavie-sjp-worker-c` on `:5683`**
  - mount: `c:/clawstack_satellite` + `c:/lavie_usb_pack`
  - `CAE_TE_WORKSPACE=/c/...`, jobs on C:（空き ~256 GB 級）
- 更新ファイル:
  - `data/workspace/lavie_node_registry.json`
  - `data/workspace/cae_workload_router.yaml`
  - `data/workspace/lavie_te_allocation_overrides.json`（`inlet_velocity: [6.0, 7.0]`）
  - `scripts/lavie_job_worker.py`（Prefer C / `_drive_free_gb`）
  - `scripts/k10_lavie_redeploy_worker_rescue.py`
- STL / `gate_spec_center.json` / `mfalign_snappy_v001` / builder を `:5683` 経由で同期

### 成功 trial

| Key | Value |
|---|---|
| Trial ID | `resume-of-20260728-044626-bfe7` |
| Verdict | **SUCCESS** |
| Fill | **99.55%**, `fill_complete=true`, Time ~1.24 s |
| Run (Lavie) | `C:\clawstack_satellite\data\work\cae_te_workspace\runs\resume-of-20260728-044626-bfe7` |
| Run (Docker path) | `/c/clawstack_satellite/data/work/cae_te_workspace/runs/resume-of-20260728-044626-bfe7` |
| KPI | `vof_fill_kpis.json`（fill_fraction_pct 99.55） |
| Geometry | box_shell_phi20 STL + MFALIGN snappy（`cad_manifest.json`） |

注意: `k10_tri_track_cae_status.json` が古い STOPPED / 別 trial で上書きされることがある。**真の成功は上記 run_dir を正とする。**

---

## 4. Telegram 充填アニメ送信

### 正規パス

1. Lavie で run を zip（worker busy 時は **exec_bridge + docker**）
2. K10 へ PUT（upload port **5689**）
3. K10 で `moldflow_fill_video_telegram.py`（pyvista `alpha.polymer`）→ Telegram

### スクリプト

| Script | Role |
|---|---|
| `scripts/k10_lavie_fill_video_bridge.py` | bridge+docker zip/curl（既定が **E:** のまま → C: 成功 run ではパス要変更） |
| `scripts/lavie_cae_video_support.py` | K10 pull + `cae_paraview_video_delivery`（OF は `CAE_OPENFOAM_PARAVIEW_TELEGRAM=1` 必要・板見え注意） |
| `scripts/moldflow_fill_video_telegram.py` | **推奨** VOF fill MP4 → Telegram |
| `scripts/k10_send_lavie_fill_video.py` | CLI wrapper |

### Worker busy 時の注意

- `:5683` が `worker_busy`（409）のとき、shell zip は失敗する
- 回避: `http://100.87.244.46:5679/webhook/exec_bridge` +  
  `docker run --rm -v c:/clawstack_satellite/data/work/cae_te_workspace/runs:/runs -v c:/lavie_usb_pack/temp:/out alpine ...`
- PowerShell / バックスラッシュ付き `cmd` は bridge で **500** になりやすい。**docker + スラッシュパス** を使う
- 単純 `echo` は bridge OK

### 再送コマンド例（K10、run が既にローカルにある場合）

```powershell
D:\Clawdbot_Docker_20260125\.venv\Scripts\python.exe -c "
import sys
from pathlib import Path
ROOT = Path(r'D:\Clawdbot_Docker_20260125')
sys.path.insert(0, str(ROOT / 'scripts'))
import moldflow_fill_video_telegram as mfv
trial = 'resume-of-20260728-044626-bfe7'
run = ROOT / 'data' / 'cae_te_workspace' / 'runs' / trial
print(mfv.send_fill_video_for_run(run, trial, category='resin_fill_cad', host='lavie', delete_after=True))
"
```

`.env` に `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` が必要。

---

## 5. 「箱の1/4だけ見える」バグ（修正済み）

### 症状

- Telegram アニメで箱形状の約1/4しか目視できない
- KPI は 99%+ で矛盾

### 根本原因（5Why）

1. 可視化が 1/4 → `clip_box(cavity_bounds)` が +X/+Y 象限のみ残す  
2. cavity が `(0,100)×(0,10)×(0,2) m`（板フォールバック）  
3. snappy 実行パッチは `gate`、blockMesh は `inlet` → gate faces 取得失敗  
4. `_mold_cavity_geometry_m` が **gate 失敗時に cavity ごと plate フォールバック**  
5. 板フォールバックと mesh（±0.05 m 立方シェル）の交差 = 正象限のみ

### 修正ファイル

`scripts/moldflow_fill_video_telegram.py`

- blockMesh vertices があれば **必ずその cavity を使う**（plate へ落とさない）
- `_active_gate_patch`: `gate` / `inlet` を認識
- snappy `gate` 時は速度向きの gate marker（誤った blockMesh `inlet` 面を使わない）
- 腔体は wireframe のみ（ソリッド AABB が薄肉シェルを隠す）
- カメラを立方体 AABB 全体が入るよう調整
- resin が cavity 内なら `clip_box` スキップ

### 検証

- 修正後 cavity ≈ `(-0.052..0.052, -0.032..0.032, -0.002..0.052)` m
- resin span ≈ cavity の 93–96%（全象限）
- 最終フレーム 99.6% でシアン枠全体が樹脂表示 → Telegram 再送 **ok=true**

---

## 6. OpenFOAM そり（参考・未解決の期待値）

- OF warp は **PROXY_GAP**（Moldflow 等価ではない）
- 参照: `docs/knowledge/mf_vs_of_warp_rainbow_check_20260724.md`
- OF ~2 mm vs MF Trans max ~0.55 mm 級の差あり

---

## 7. Moldflow Synergy PNG/Telegram（残）

- Dynabook 上で Fill→Warp strip / Synergy deflection PNG・GIF は引き続き不安定
- COM: `StudyDoc=Nothing` / COM 462 等
- 手動 export 先候補: `G:\moldflow_bridge\work\results\mf_warp_telegram_20260727\`
- 本セッションでは未完了

---

## 8. 残作業 / 次回推奨

| Priority | Action |
|---|---|
| P0 | 継続 OF が **`:5683` / C:** のみ使うこと（E: / `:5682` 回帰禁止） |
| P1 | `k10_lavie_fill_video_bridge.py` の既定 run/temp を **C:** に合わせる（または `--run-vol` 引数化） |
| P1 | tri-track status JSON の race（成功後に STOPPED 上書き）を調査 |
| P2 | Moldflow Synergy 可視化 → Telegram |
| P2 | INCIDENT_LOG / Obsidian に 1/4-box viz を正式 INC 追記（コード修正は済） |

---

## 9. 品質メモ（短）

| 観点 | 内容 |
|---|---|
| QC | Telegram 送信前に mid/final PNG を目視（箱全体・ゲート位置） |
| FMEA | plate cavity フォールバック × clip_box → 象限欠損（再発防止: vertices 優先） |
| Meaning gate | `fill_complete=true` 必須（P026）。板ジオメ / resin_flow 禁止（T019） |

---

## 10. 関連パス一覧

```
D:\Clawdbot_Docker_20260125\docs\handover\LAVIE_OF_C_WORKER_AND_FILL_TELEGRAM_QUARTERBOX_20260728.md
D:\Clawdbot_Docker_20260125\scripts\moldflow_fill_video_telegram.py
D:\Clawdbot_Docker_20260125\scripts\k10_lavie_fill_video_bridge.py
D:\Clawdbot_Docker_20260125\scripts\lavie_cae_video_support.py
D:\Clawdbot_Docker_20260125\data\workspace\lavie_node_registry.json
D:\Clawdbot_Docker_20260125\data\workspace\cae_workload_router.yaml
D:\Clawdbot_Docker_20260125\data\cae_te_workspace\runs\resume-of-20260728-044626-bfe7\
```

Lavie:

```
C:\clawstack_satellite\data\work\cae_te_workspace\runs\resume-of-20260728-044626-bfe7
C:\lavie_usb_pack\
```

---

*Written: 2026-07-28 (session: Lavie C: worker + Telegram fill quarter-box fix)*
