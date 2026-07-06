# T051: red_lavie gates版数不整合による偽ERROR + tri-trackループ停止 (2026-07-06)

bd: `tq1`(P0, blanking完走) 関連 / 系統: T049→T050の追補

## 事象
- 7/6 01:47 (`tri-red_lavie-press_blanking_assy-4083178d`) と 02:55 (`8410e899`) の2試行が verdict=ERROR
- **実際はソルバは NORMAL TERMINATION に到達**(物理計算成功)。判定段階の
  `defects_detected.assessment_error = "module 'cae_self_growth_gates' has no attribute 'parse_openradioss_run_metrics'"` で評価が失われた
- 併発: K10 tri-track オーケストレータが **7/6 03:29 JST を最後に停止**(status/log更新途絶)

## 真因
- T050復旧(7/5 23:30)で red_lavie へ `cae_te_engine.py` **のみ**配布。7/4 23:40 に
  `parse_openradioss_run_metrics` が追加された `cae_self_growth_gates.py` を配布せず → 版数不整合
- 根本: **engine/gates をペア配布する規定が無かった**(FTA終端)

## 実施済み (2026-07-06, K10リポジトリ)
- `scripts/cae_te_engine.py:1867` に hasattr ガード追加。gates旧版検出時は
  `T051_GATES_VERSION_MISMATCH` タグ付きで fail-fast(偽ERROR・原因不明化を防止)。py_compile OK

## 残作業 (次セッション / ユーザー実施)

### 1. red_lavie へペア配布 — ✅ **完了(2026-07-07未明)** `k10_t051_deploy_all_in_one.ps1` でSHA256照合付き配布成功。以下は記録として保持。
**配布時の3つの罠(恒久教訓):** ①certutilはワーカーのサービス文脈でWinINet起因の無言失敗→Invoke-WebRequestを使う ②ワーカーは単線・syncジョブ実行中は/jobsが全ブロック→配布前にorchestrator全停止が必須 ③watchdogは2重起動を検知しない(pid複数表示が兆候)

(旧手順: T050と同方式: SHA256検証+py_compile必須)
| ファイル | SHA256 (K10正) |
|---|---|
| `scripts/cae_te_engine.py` (T051ガード入り) | `f63f174f334b46e92c68a184de047084cec770c16ca7ae3378b1e4c9cbee3e09` |
| `scripts/cae_self_growth_gates.py` | `39e0b6f4422e35f6aec47f81ee37a1fa4a12759011cd8adec484f636d70e3c17` |

- 配置先は red_lavie 側の既存 `cae_te_engine.py` と同ディレクトリ(**仮定: `C:\clawstack_satellite\scripts` — 配布前に実パス要確認**。T050バックアップ `.bak_t050` が目印)
- 配布後: 両ファイル SHA256照合 → `python -m py_compile` → バックアップ `.bak_t051` 作成

### 2. tri-track オーケストレータ再起動 (K10)
```powershell
powershell -ExecutionPolicy Bypass -File D:\Clawdbot_Docker_20260125\scripts\start_k10_tri_track_cae_watchdog.ps1
# 確認: data\workspace\k10_tri_track_cae_status.json の updated_at が進むこと
```
- 停止時刻03:29はClaudeCodeクラッシュと同時間帯。再発時は watchdog 側ログも確認

### 3. bd 登録
```bash
bd update Clawdbot_Docker_20260125-tq1 --comment "T051: 7/6の2試行はNORMAL TERMINATION到達済みだがgates版数不整合で偽ERROR。engineガード追加済み、red_laviéペア配布とオーケストレータ再起動が残"
bd create --title "[bug] T051 red_lavie gates版数不整合で偽ERROR + engine/gatesペア配布ルール恒久化" --priority 1
```

### 4. 恒久ルール
**衛星へ engine を配布する時は必ず `cae_self_growth_gates.py` とペアで配布し、両方のSHA256を照合する。**

## 追記 (2026-07-06 午後): 5yk DXF-QC04c 弧無視偽FAIL修正 + ThinkPad配布

- **真因:** `_wire_graph_stats` がLINEのみで位相判定しARCを無視 → 線-弧-線の閉輪郭(S1: line102+arc101)で `open_endpoints=174` の偽FAIL(`tp-dxf-963a5926`)
- **修正:** `data/workspace/apps/dxf2step/dxf2step_worker.py` `_evaluate_closed_loop_qc` に弧の弦を位相グラフへ追加。SHA256(Windows実体・CRLF): `f43cafbb9b7a3df3c920cff6d56d1d078658f0af776eb915e9c027a292804f7b` — **2026-07-06 ThinkPadへ配布済・一致確認済**(grep 919/940行でマーカー確認、py_compile OK。バックアップ`.bak_5yk`)
- **検証:** py_compile OK / 単体テスト3件PASS(S1型偽FAIL解消・真の開輪郭は依然FAIL・円のみパンチは依然FAIL)
- **配布必須(ペア配布ルール):** workerはThinkPadの配置コピーが実行される(自動同期なし)
  ```powershell
  scp D:\Clawdbot_Docker_20260125\data\workspace\apps\dxf2step\dxf2step_worker.py yasu@<thinkpad>:/home/yasu/clawstack_satellite/apps/dxf2step/
  # ThinkPad側で: sha256sum 照合 → python3 -m py_compile → バックアップ .bak_5yk
  ```
- **bd:** `bd update Clawdbot_Docker_20260125-5yk --comment "QC04c弧無視の偽FAIL修正+単体テストPASS。ThinkPad配布後にS1再試行で実機確認"` / 0wf はT042対策実装済+監査スクリプト存在確認済 → `audit_dxf2step_hole_vs_island_misclass.py` 再実行でクリーンなら close 可
- **注意:** ThinkPad dxf2stepループは現在旧コードで稼働中(7/6 15:57確認)。worker配布は次回試行から自動反映されるが、K10側ループの意味ゲート(ip4)はループ再起動まで無効

## 追記2 (2026-07-06 夕): 5yk-2/5yk-3 — S1偽FAILの完全解明(3層の原因)

S1 (`tp-dxf-963a5926`→`af3eda2b`) の QC04c 偽FAILは3つの実装漏れの複合だった:

1. **5yk-1: 弧無視** — 位相グラフがLINEのみ。弧の弦を追加(open 174→108)
2. **5yk-2: 注記線種混入** — DASHDOT/DOT/DIVIDE等の中心線・ピッチ円が形状扱い。`clean_geometry`冒頭に`ANNOTATION_LINETYPES`フィルタ追加(open 108→28、注記円23個除去、外形線復活)
3. **5yk-3: T字接合誤カウント** — 開放端点28個は全て他セグメント内部に着地(距離0.000)=T-junction。①内部接触端点をopenから除外 ②閉成分判定を「全節点次数2」→「サイクル保有(edges≥nodes)」に変更(T分岐込みの外形33600mm²を閉と認識)
- **検証:** 実S1データのオフライン再現で pass=True (open=0, t_junction=28, closed_max=33600, ratio=1.224 — 実機trial値と一致)。回帰3件PASS(真の開輪郭FAIL維持・円のみパンチFAIL維持)
- **教訓:** 実図面は「注記幾何の混在」「T字接合」「線-弧混成輪郭」が常態。位相QCはこの3つを前提に設計すること
- **残確認:** QC04c通過後のFreeCAD押し出し・穴カットQC(QC04d以降)は未踏。S1再試行の実機結果で判断

6. **5yk-6: QC04g島リスク誤判定** — 5yk-5後、FreeCADは1外形+13切欠きを正しくネスト解決し造形成功(V=147910mm³, 241面, 座ぐり付き)したのに、worker側QC04gが「非円ワイヤ14>1=島リスク」と生カウント判定でSTEPを削除。対策: FreeCADスクリプトが `[hole-cut] base_faces=N`(ネスト解決後の独立外形数)を出力し、QC04gは base_faces≠1 の時のみFAIL(マーカー無し旧スクリプトは0扱い=fail-closed維持)。T041バラ図対策はNG_MULTIPLE_PROFILES例外で不変

5. **5yk-5(真の最深層): 重ね書き境界線の削除** — 外形縦辺(3609.8, 125.6→325.6)の上に短線(280.1→305.1)が重ね書きされており、`resolve_tjunctions`の「2回出現サブセグメント=内部共有辺→削除」ルールが外形の25mm区間ごと削除→外形破断。対策: 削除で端点が宙に浮く(次数≤1)場合のみ1本復元(真の内部壁は両端が接続維持のため復元されない)。**完全再現パイプラインでS1 QC04c通過を確認**(restored 2 spans, open=0, closed_max=33600, pass=True)

4. **5yk-4: 外形の実ギャップ** — 5yk-3後の実機で open=2 が残存 = 外形が1箇所実際に切れている(図面由来1-2mm級ギャップ)→ サイクル不成立で閉成分205mm²のまま。`_heal_endpoint_gaps` を実装: 真の開放端点(次数1・T接触なし)の相互最近傍ペアを `DXF2STEP_GAP_HEAL_TOL`(既定2.5mm)以内で橋渡し。橋はsub-DXFにも書かれFreeCADの面生成にも効く。テスト: 1.5mmギャップ修復→QC PASS / 5mm非修復→FAIL維持 / T字スタブ誤修復なし / env上書き動作
- 2試行のパラメータ: clearance 10.7% / 11.7%, punch_speed 2039 / 2475 mm/s, μ 0.107 / 0.095
- engineログに `NODAL VELOCITY IS TOO HIGH FOR INTERFACE 1` あり → 再開後、KPI評価が正常化したら
  punch_speed 低め側の探索を優先する余地あり
- red_lavie 温度ガード(76°C)による SKIP_LOAD が 03:00-03:04 に発生。T050の電源プラン修正後の
  クロック1792MHz常用で温度余裕が減っている可能性 → 再開後の温度推移を監視
