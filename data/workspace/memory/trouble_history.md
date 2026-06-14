# IATF 3D Video Pipeline Trouble History & Lessons Learned

> **全エージェント作業前に必読（最優先）:** **[T019] 北極星・意味ゲート** — 無意味な繰り返し・最終目標喪失の禁止。樹脂充填だけでなく **あらゆる活動** に適用。

| ID | 日付 | 事象 | 対策 |
| --- | --- | --- | --- |
| **[T034]** | **2026-06-14** | **サテライトPC（LAVIE, Red LAVIE, G3）の24時間稼働率が70%以下に低下（LAVIE: 41.7%, Red LAVIE: 0.8%, G3: 0.0%）。ホスト再起動後のサービス自動起動の不備およびVBS起動スクリプトの構文バグ、Tailscaleの切断が真因。** | **①Red LAVIEのVBS構文バグ（Chr(34)二重括りによるファイル不在エラー）を修正し、スタートアップ登録を再定義。②G3およびLAVIEのスタートアップにDocker compose/n8n自動起動用のタスクスケジューラを恒久化。③Tailscale接続の定期監視スクリプトを有効化。** |
| **[T033]** | **2026-06-14** | **メカ自動リグに「関節分離防止ルール」が存在しない: 腕がT字内転で完全脱離・腿が股で割れる。剛体ボーンペアレント＋pivotがBB比率ハードコード(実関節軸でない)＋LIMIT_ROTATIONのみ→回転で隙間、大回転で脱離** | **設計ルール①〜④をリグビルダーに実装中**: ①pivot=実形状の関節中心(メッシュ算出) ②オーバーラップ・ジョイントコア(ball球/hinge円柱を子ボーンにバインドし隙間を物理的に埋める) ③可動域=無隙間レンジに自動制限 ④分離QCゲート`qc_joint_separation.py`(親子セグメント最小距離の成長を可動域スイープで計測しFAIL判定)。目視は**5フレーム毎×前/横/後**`qc_multiview.py`必須(hero1枚禁止)。bd `Clawdbot_Docker_20260125-exs`/`bd recall mecha-rig-joint-integrity-t033`。T031/T032系統 |
| **[T032]** | **2026-06-14** | **ザク歩行アニメ false-PASS リスク: ①前進を Root pose-bone.location に書き床に沈下（pose-bone はボーン rest ローカル空間／Root は鉛直→ローカルY=世界Z）②股関節が大角スイングで剛体ヒンジ隙間を露出** | **①前進・bobは`armature.location`（世界空間オブジェクト）にキー、pose-boneは回転のみ ②数値ゲート強化(前進>WALK*0.5 + 接地min z>-0.5) ③視覚QA必須(沈下/裂け目確認) ④HIP18°→11°/KNEE35°→22°で剛体隙間縮小。完全除去はリグ側(境界分割/スカート重なり)。T031/T015同系統** |
| **[T031]** | **2026-06-14** | **メカ自動リグ false-PASS: 形状崩壊ザクに "ALL PASS" 判定しTelegram送信** | **3根本原因修正**: ①`remove(armature)`→`parent_clear(KEEP_TRANSFORM)` ②auto-detect直立時rotation上書き禁止 ③`_geometric_quality_gate()`追加(直立比/接地/対称)でvisual QA必須化。T019/T018同系統 |
| **[T030]** | **2026-06-07** | **G3 `monitor_agent` 27.9°C fallback — repo パス不在・8112 旧 agent・LHM :8085 Run 未設定** | **INC-096 拡張** + `fleet_lhm_monitor_agent_runbook.md` + G3 検証 63°C lhm_http + サーマル制御共通化 |
| **[T029]** | **2026-06-07** | **K10 `monitor_agent` が CPU 27.9°C（fallback 誤値）を報告 — LHM Remote Web Server 未起動 + `data.json` パーサが `Type`/文字列 `Value` 非対応** | **INC-096** + `monitor_agent.py` LHM HTTP パーサ修正 + `lhm_ok`/`temp_source` 可視化 + 起動順 SOP（LHM 8085 → monitor_agent 8111）+ `docs/troubleshooting/k10_lhm_monitor_agent_20260607.md` |
| **[T021]** | **2026-06-04** | **各サテライトPC（G3, LAVIE, Dynabook）およびK10の障害が検知されつつ長期間放置 — 監視項目の単純死活（HTTP/ポート）依存、自己修復ループ欠落** | **INC-095** + `update_fleet_operations_status.py`の容量・最終更新トラッキング強化 + `autonomous_coder.py`の`--allow-offline`実装 + タスクスケジューラでのスタートアップ起動登録恒久化 |
| **[T020]** | **2026-06-03** | **OpenRadioss 連続 T&E (`press_blanking`/`press_bending`/`press_blanking_stripper`) が ~1s ERROR TERMINATION — デック構文・中面メッシュ不備** | **INC-094** + pregate (`cae_self_growth_gates.py`) + DBEND形式テンプレ + bd `openradioss-continuous-te-inc094` + starter-only 検証必須 |
| **[T019]** | **2026-06-02** | **LAVIEが`resin_flow`（薄管icoFoam）で24/7 T&Eし2D ParaView \|U\|をTelegram送信 — 射出キャビティ充填・順送金型目標と無関係** | **P025** + `docs/cae_north_star_and_meaning_gate_protocol.md` + Meaning Gate必須 + `resin_fill_cad`/閉キャビティVOF + ParaView2D禁止 + bd/ByteRover定着 |
| [T001] | 2026-04-20 | PDFテキスト抽出時の文字化け | `pdfminer.six` から `PyMuPDF (fitz)` へ切り替え、エンコーディング処理を強化。 |
| [T002] | 2026-04-22 | Blender Headless レンダリング時の GPU エラー | Windows 仮想ディスプレイアダプタを導入し、バックグラウンドでの OpenGL コンテキストを安定化。 |
| [T003] | 2026-04-25 | VoiceVox API のタイムアウト | 生成リクエストをチャンク分割（100文字単位）し、リトライロジックを実装。 |
| [T004] | 2026-04-28 | キャラクターボーンのねじれ (Mesh Skinning) | ウェイトペイントの正規化と、Blender Python API による正規化スクリプトを自動実行。 |
| [T005] | 2026-05-01 | OpenCode GO API の不安定化 | LiteLLM による冗長化（Gemini 2.5 Flash / Claude 3.5 Sonnet）と優先順位制御を導入。 |
| [T006] | 2026-05-03 | スライドレイアウトの崩れ | AI Visual Review Gate を導入。動画合成前に AI がスライドの整合性をチェック。 |
| [T007] | 2026-05-05 | リップシンクのズレ | VoiceVox の `query.json` から正確な音素時間を取得し、Blender の F-Curve に直接流し込む方式へ改善。 |
| [T008] | 2026-05-06 | Excel 報告書 XML 破損 | `RubyXL` の `merged_cells` 配列を書き込み前に一旦クリアし、重複範囲を除去するクリーンアップ処理を実装。 |
| [T009] | 2026-05-07 | T-Pose モデルのテクスチャ剥がれ | Stable Projectorz の PBR ベイク工程に自動 UV リラップを追加。 |
| [T010] | 2026-05-08 | VoiceVoxコンテナのハングアップ | Service Guardian (v1.2) を導入し、L3/L4死活監視と自動再起動を常駐化。 |
| [T011] | 2026-05-08 | QA不合格（Wチェック）の教訓の未利用 | IATF自律学習サイクル (AFL) を実装。不合格理由を教訓として蓄積し、全生成プロンプトへ自動注入。 |
| [T012] | 2026-05-09 | キャラクター透明化・重複・QA形骸化 | 統計的QAを廃止し Kimi K2.6 によるマルチモーダル目視チェックを必須化。Blenderマテリアル不透明固定を強制。 |
| [T013] | 2026-05-10 | Blenderレンダリング全フレーム黒（global_scale二重適用） | `global_scale=0.01` × FBX内蔵スケール0.01 → 0.0001倍（0.2mm）でカメラに映らず全黒。`global_scale=82` に修正。**なぜなぜ**: ①黒→②キャラ不可視→③スケール0.2mm→④FBX出力時に既存0.01スケール埋込済なのに再適用→⑤FBXのUnitScaleFactor未確認で慣例値を使用。**対策**: FBX新規追加時はdiag5スクリプトで`world_height`を必ず測定してからglobal_scaleを決定。 |
| [T014] | 2026-05-10 | 3Dシーンの大道具・小道具・背景がPDF内容と無関係 | **実装完了**。`CLAUSE_SCENE_MAP`（17箇条カテゴリ）＋`derive_scene_context(topic)`＋`setup_environment(scene_ctx)`を`blender_animator.py` V5.0に実装。床・背景壁・看板・小道具（6種）を箇条番号に応じて自動生成。`run_host.py`・`orchestrator.py`にもtopicパラメータを接続済み。**追加バグ(T015候補)**: MixamoモーションFBX（UnitScaleFactor=1.0）を`global_scale=82`でインポートするとarm.scale=82となり、アクションのボーントランスレーションが82×膨張→キャラが800m以上離れてカメラ外に飛ぶ。**暫定対策**: apply_motionを無効化（キャラはTポーズ静止）。正式対策は別タスクでMixamoFBX用global_scaleの再算出が必要。 |
| [T015] | 2026-05-10 | MixamoモーションFBX適用後キャラが画面外に消失（全黒） | **真因**: `pose.bones["mixamorig:Hips"].location[1]` キーフレーム値≈50.17（armatureローカル）。`arm.scale=0.82` → ワールドY=**41.14m**でカメラ外飛散。Blender5.1の`action.fcurves`廃止でF-Curve取得エラーも複合。**最終対策（確認済）**: `rotation_quaternion`/`rotation_euler`/`rotation_axis_angle` F-Curveのみコピー（520本→**208本**）。locationとscaleは全除外。ボーン名はキャラ/MixamoともにmixamoRig:プレフィックス付きで直接互換。ログ確認: `208 bone F-curves (OBJ-level excluded, T015)`。 |
| [T016] | 2026-05-11 | T015修正後にバッチが再起動されず全本が未完成のまま放置 | **真因**: コード修正完了の確認手順・バッチ再起動トリガーが存在しない。T015修正→テスト合格→バッチ再起動の一連フローが定義されていなかった。**副因**: Visual QA `sample_frames_are_nearly_identical` 否決（Tポーズ静止フレーム）がバッチを即停止する設計で復旧手順なし。**対策（本セッション実施）**: ①停止検知→Telegram通知→自動再起動フックをrun_host.pyに追加。②FPS30→12,samples32→12に変更し1本あたり推定時間を17h→2h以内に短縮。③PDF本文キーワード→props動的マッピングを実装。なぜなぜ6段・FMEA・FTA記録済み。 |
| [T018] | 2026-05-31 | 品質ゲート形骸化（方針のみ・FAIL続行・偽合格通知） | `gate_registry.py` fail-closed + PROMISES P024 + `docs/iatf_gate_enforcement_protocol.md` + 監査 `iatf_audit_legacy_outputs.py` |

---

## [T020] OpenRadioss 連続 T&E デック構文不整合 (2026-06-03)

**事象:** K10 連続 T&E ループ (`k10_openradioss_continuous_te_loop.py`) の `press_blanking` / `press_bending` / `press_blanking_stripper` がすべて ~1s で FAILED。Starter/Engine ログ: ERROR 21 (SHELL NEGATIVE/NULL SURFACE), 402 (PART 0), 1051 (BCS), IMPDISP parse error。物理計算 (NORMAL TERMINATION) に一度も到達しなかった。

**North Star 整合 (T019):** 本件は順送金型向け OpenRadioss 曲げ/打ち抜き T&E の **入力品質** 問題。修正後 `inc094e-*` trial で NORMAL TERMINATION を確認 (blanking 17 cycles, bending 230 cycles)。

### 根本原因

1. **板厚の誤配置:** `/PROP/SHELL` の `hm` (hourglass 0-0.05) に 1.2mm を設定、または Y 方向ノードオフセットで厚み表現 → ERROR 21。
2. **PROP 2024 形式非準拠:** `N Istrain Thick ...` の `Istrain` 余分フィールド、`# h` 短縮形式 → 厚み 0 または誤読。
3. **IMPDISP 1行混在:** fct/dir/grnod/Tstart/Tstop 混在 → OpenRadioss 2024 parse fail。
4. **legacy /SHELL, /BCS, engine block in starter** — INC-093 途中修正で段階的に解消。

### 対策 (再発防止)

| 項目 | 内容 |
|---|---|
| テンプレート | 中面 X-Z (y=0); `/PROP` → `Thick` 行; `/IMPDISP` 2行; `/SHELL/pid`; GRNOD>=100 |
| pregate | `precheck_openradioss_case`: engine block, GRNOD clash, thickness-in-geometry |
| 検証手順 | 新 deck は **starter-only** → `.rst` 確認 → engine → NORMAL TERMINATION |
| 記録 | INC-094, bd `openradioss-continuous-te-inc094`, ByteRover |

### FMEA / FTA / 5Why / Logic Tree

詳細は `docs/INCIDENT_LOG.md` **INC-094** を参照（FMEA RPN表、FTA 木、6段なぜなぜ、ロジックツリー完備）。

---

## [T019] 北極星喪失・無意味CAEループ（resin_flow / 2D |U|）(2026-06-02) — 全活動最優先

**事象:** ユーザーはキャビティへの樹脂充填・成形条件調整・3D可視化を求めていたが、LAVIE連続T&Eは `lavie_te_allocation_overrides.json` により **`resin_flow`（矩形ダクト・icoFoam層流）** のみを実行。SUCCESS時に **ParaView 2D |U|** をTelegramへ送り、「忙しく見えるが順送金型・射出成形に無関係」な繰り返しが続いた。エージェントは「動画を送る」要求に引っ張られ、**物理目標とカテゴリ/ソルバの整合**を先に検証しなかった。

### 北極星（最終目標 — 見失ってはならない）

ユーザー提供の **プレス部品3Dモデル** から:

1. **Moldflow級** — 閉キャビティ樹脂充填（VOF・ゲート・パック）の正しいT&E  
2. **Cetol 6 Sigma級** — 公差・スタックアップの正しい解析  
3. **OpenRadioss** — **曲げ**・**打ち抜き**の正しい解析  

→ これらを統合して **順送金型（プログレッシブダイ）開発** を完遂できること。

### なぜなぜ（要約）

| Why | 観察事実 |
| --- | --- |
| ①なぜ無意味？ | 充填ではなくダクト内速度場を見ていた |
| ②なぜダクト？ | カテゴリが `resin_flow` / `resin_flow_v001` 固定 |
| ③なぜ気づかない？ | ループ稼働＝進捗と誤認；Telegram出力＝価値と短絡 |
| ④なぜ検証なし？ | Meaning Gate（物理⇔カテゴリ）がコード・ルール化されていなかった |
| ⑤なぜ繰り返す？ | 失敗してもカテゴリを変えず nu/U だけスイープ |

### FMEA（抜粋）

| 工程 | 故障モード | 影響 | 対策 |
| --- | --- | --- | --- |
| 要件解釈 | 可視化形式だけ実装 | 目的逸脱 | Meaning Gate 5問必須 |
| 割当 | resin_flow 固定 | 充填未達 | overrides → resin_fill_cad + closed_pack |
| 通知 | 2D \|U\| 送信 | 誤判断・ノイズ | `_openfoam_skip_paraview` + VOF MP4のみ |
| 充填動画 | LAVIEでffmpeg無し・notifyだけ成功扱い | SUCCESSなのに動画無し | INC-089: K10 pull (`lavie_cae_video_support`); host=lavieはengine送信禁止 |
| 記憶 | 教訓未定着 | 再発 | P025 + T019 + bd + ByteRover + Cursor rule |

### 意味ゲート（毎セッション・毎タスク前）

1. 何の物理現象か？  
2. category / solver / physics_category は一致しているか？  
3. どのKPIが北極星に1mmでも近づくか？  
4. 無意味な繰り返しではないか？  
5. 今回の学びを bd / ByteRover / 本節に残すか？  

**1つでもNOなら実行停止・修正してから再開。**

### 恒久対策（忘禁）

1. **PROMISES P025**（本ファイル最上部）  
2. **`docs/cae_north_star_and_meaning_gate_protocol.md`**（単一真実）  
3. **`.cursor/rules/cae_north_star_meaning_gate.mdc`**（alwaysApply）  
4. **`bd remember --key cae-north-star-t019`** / Beads `Clawdbot_Docker_20260125-3z1`  
5. **ByteRover** `brv curate` で全セッション前 query 推奨  

**参照:** `lavie_te_allocation_overrides.json`, `scripts/cae_te_engine.py` `_openfoam_skip_paraview`, `scripts/k10_lavie_continuous_te_loop.py`

---

## [T018] IATF動画：ユーザー要求の品質ゲートが守られなかった (2026-05-31) — 詳細分析

**事象:** ユーザーは繰り返し「QC工程表・FMEA・FTA・なぜなぜ・Fishbone・出演者/背景/照明/カメラ配置・画像/動画崩壊チェック・Script QA」を**生成開始前に必須**と指示していたが、実際には (1) LLM事前分析がサイレントスキップ (2) Script QA FAIL のまま TTS/レンダ継続 (3) Telegram が不合格でも「合格」表示 (4) 38/40 フォルダに `quality_preflight.json` 無し (5) 27 本以上が FAIL/ERROR 台本のまま MP4 化、が発生した。

### なぜ守られなかったか（根本原因）

| Why | 観察事実 |
| --- | --- |
| ①なぜ要求が効かない？ | エージェント/バッチがゲートを通らずに生成した |
| ②なぜ通らない？ | ルールが `CLAUDE.md` 等の**文書のみ**で、Python が FAIL 時に `raise` していなかった |
| ③なぜ raise しない？ | `quality_preflight.py` が「LLM失敗時はサイレントスキップ」と明記され `{}` で続行していた |
| ④なぜ FAIL でも続行？ | `run_host.py` が Script QA の `overall==FAIL` 後も TTS へ進み、Telegram で常に合格メッセージを送っていた |
| ⑤なぜ再開で抜ける？ | resume 時に `script.json` があると工程 1.5〜2.5 をスキップする設計だった |
| ⑥なぜエージェントが省略？ | `.cursor/rules` に IATF 専用ルールがなく、セッションごとに `CLAUDE.md` を読まない |

### 各工程で実際に起きた問題と、効いた対策

| 工程 | 実際の問題 | 効いた対策 |
| --- | --- | --- |
| 品質事前分析 | 未実行 or 空 JSON；FMEA が台本に未反映 | `quality_preflight.json` 必須 + `QualityPreflightError` |
| 台本 QA | 6/7 FAIL で TTS 開始；API 浪費 | `script_qa_gate.py`：PASS のみ続行 |
| 通知 | FAIL なのに「台本Wチェック合格」 | PASS 時のみ Telegram `[PASS]` |
| 制作レイアウト | 未知キャラ・背景無関係・全黒・静止画 PASS | `production_design.json` + Visual QA checklist |
| Visual QA | 401 で自動合格；統計のみでシルエット PASS | 401 バイパス削除；R08-R13 + V01-V06 |
| 再開 | 古い NG 台本のままレンダ | resume でも `_ensure_*` + `gate_registry` |
| 監査 | 過去 MP4 が合格か不明 | `scripts/iatf_audit_legacy_outputs.py` |

### FMEA（抜粋）

| 工程 | 故障モード | 影響 | S | O | D | 対策 |
| --- | --- | --- | --- | --- | --- | --- |
| 要件定義 | 方針のみでコード未接続 | 再発 | 9 | 8 | 3 | `gate_registry.py` 単一真実 |
| 事前分析 | LLM 失敗スキップ | 無分析生成 | 8 | 7 | 2 | fail-closed |
| Script QA | FAIL 続行 | API・時間浪費 | 9 | 9 | 2 | `ScriptQAError` |
| 通知 | 偽合格 | 誤判断 | 7 | 6 | 2 | PASS 時のみ通知 |
| 監査 | 過去品不明 | 誤配布 | 8 | 9 | 4 | 監査スクリプト |

### FTA（頂上事象：ユーザー要求が守られない）

```text
要求不履行 (TOP)
├─ [OR] コードが止めない
│   ├─ サイレントスキップ (quality_preflight)
│   ├─ FAIL でも TTS (run_host 旧版)
│   └─ resume バイパス
└─ [OR] 人間/エージェントが省略
    ├─ CLAUDE.md のみ（実行不可）
    └─ Cursor rule なし
```

### 恒久対策（必須・忘禁）

1. **単一真実:** `pipeline/gate_registry.py` + `docs/iatf_gate_enforcement_protocol.md`
2. **PROMISES P024:** IATF 動画はゲート artifact なしで TTS/レンダ禁止
3. **Cursor:** `.cursor/rules/iatf_gate_enforcement.mdc`（alwaysApply）
4. **作業前:** `trouble_history.md` T018 と `bd remember --key iatf-gate-t018`
5. **過去品:** `python scripts/iatf_audit_legacy_outputs.py` で再監査

**参照:** INC-101, `docs/iatf_gate_enforcement_protocol.md`

---

## [T015] Mixamoモーション適用後キャラが画面外消失 (2026-05-10) — 詳細分析

### 最終確定した真因と対策

- **真因**: `pose.bones["mixamorig:Hips"].location[1]` ≈ 50.17（アーマチュアローカル空間絶対位置）。`arm.scale=0.82` → ワールドY=41.14m → カメラ（Y≈4m）から37m外。
- **複合要因**: Blender 5.1で`action.fcurves`属性が廃止→AttributeError → `action.layers[].strips[].channelbags[].fcurves`が正しいAPI。`ActionSlots.new()`の引数も変更（`id_type`+`name`両方必須）。
- **最終対策**: `rotation_quaternion`/`rotation_euler`/`rotation_axis_angle` のF-Curveのみコピー（520本→208本）。`location`と`scale`は全除外。
- **確認ログ**: `[BLENDER] Motion applied: 208 bone F-curves (OBJ-level excluded, T015)`
- **ボーン名**: キャラ/MixamoともにBlenderインポート後は`mixamorig:`プレフィックス付き → プレフィックス除去不要、直接互換。

### なぜなぜ分析（最終版）

| Why | 観察事実 |
| --- | --- |
| ①なぜ全黒？ | キャラクターがカメラに映っていない |
| ②なぜ映らない？ | キャラクターがワールドY≈41mに飛散 |
| ③なぜ41m？ | `Hips.location[1]`キーフレーム値≈50.17（armatureローカル）× arm.scale=0.82 |
| ④なぜ50.17？ | Mixamo FBXはHipsボーンのワールド位置をlocationキーフレームに絶対値で記録する仕様 |
| ⑤なぜlocationを使った？ | rotation F-Curveだけでなくlocation F-Curveも無差別にコピーしていた |
| ⑥なぜ無差別？ | apply_motion()実装時にF-Curveのdata_pathを確認せず全転用した |

**再発防止**: 新規モーションFBX適用前に`blender_kf_values.py`でHips.location値を確認し、50以上ならlocation除外モードを使用する。

### FMEA (Failure Mode and Effects Analysis)

| 工程 | 故障モード | 影響 | 深刻度(S) | 発生確率(O) | 検出容易性(D) | RPN | 対策（実施済） |
| --- | --- | --- | --- | --- | --- | --- | --- |
| FBXインポート | OBJECTレベルlocation keyframe持込 | キャラ画面外飛散 | 10 | 7 | 2 | 140 | **✅** rotation系のみコピー（520→208本）、location/scale全除外 |
| スケール設定 | global_scale不整合 | world_height×82膨張 | 8 | 5 | 3 | 120 | **✅** 新規FBX追加時にblender_kf_values.pyでworld_height実測 |
| アクション転用 | 転用先と転用元のarm.scale不一致 | ボーンアニメ破綻 | 7 | 4 | 4 | 112 | **✅** インポート後arm.scaleをログ出力して比較 |
| レンダリングゲート | 全黒フレームを合格と誤判定 | 不良品流出 | 9 | 6 | 2 | 108 | **✅** visual_qa.py: dark_ratio_median>0.90で`all_black_frames`失敗を追加 |

### FTA (Fault Tree Analysis)

```text
全黒レンダ（TOP事象）
├─ [OR] カメラ外にキャラ消失
│   ├─ [AND] アーマチュアがz>10m
│   │   ├─ OBJECTレベルlocation keyframeあり（Mixamoの仕様）
│   │   └─ global_scale=82で倍率増幅（開発者の設定ミス）
│   └─ 子オブジェクト位置二重オフセット（T015修正済）
└─ [OR] マテリアル発光なし
    ├─ Emission未接続（→T013/T014で修正済）
    └─ use_nodes=True設定漏れ（Deprecation対応未完）
```

**重要な教訓**: FBX由来のアクションを別アーマチュアに転用する際は、必ずF-Curveのdata_pathを全数確認し、`pose.bones`プレフィックス以外のF-Curveが含まれていないかチェックすること。

---

## [T016] バッチ修正後の再起動漏れ・全本未完成放置 (2026-05-11) — 詳細分析

### なぜなぜ分析

| Why | 観察事実 |
| --- | --- |
| ①なぜ全41本が未完成？ | バッチが停止したまま再起動されなかった |
| ②なぜ再起動しなかった？ | T015修正完了後のバッチ再起動手順が存在しなかった |
| ③なぜ手順がない？ | バグ修正→テスト合格→バッチ再起動を一連のフローとして定義していなかった |
| ④なぜフローがない？ | CI/CD（コード修正→本番反映）の概念をバッチ処理に適用していなかった |
| ⑤なぜ適用しなかった？ | バッチは「手動起動するもの」という前提があり、自動継続の設計がなかった |
| ⑥なぜその前提？ | パイプライン初期設計時に長時間バッチの運用フローを定義しなかった |

**再発防止**: コード修正完了時に `run_host.py --restart-failed` を必ず実行するルールを確立。

### FMEA

| 工程 | 故障モード | 影響 | S | O | D | RPN | 対策（実施済） |
| --- | --- | --- | --- | --- | --- | --- | --- |
| バグ修正後 | バッチ再起動漏れ | 全本未完成 | 9 | 8 | 1 | 72 | **✅** 修正完了時に再起動フックを追加 |
| Visual QA否決 | バッチ即停止・無復旧 | 全本停止 | 8 | 7 | 2 | 112 | **✅** QA否決時に自動スキップ+Telegram通知へ変更 |
| レンダリング速度 | 1本17h×41本=29日 | 現実的でない納期 | 7 | 10 | 1 | 70 | **✅** fps30→12, samples32→12で推定2h/本に短縮 |
| PDF内容非適合 | 汎用小道具のみ | 教育効果が低い | 6 | 9 | 3 | 162 | **✅** PDF本文キーワード→props動的マッピング実装 |

### FTA

```text
全本未完成（TOP事象）
├─ [AND] バグ修正完了
│   └─ バッチ再起動なし
│       ├─ 再起動手順が未定義（設計漏れ）
│       └─ 停止通知が届かない（Telegram未設定）
└─ [OR] Visual QA否決でバッチ停止
    ├─ sample_frames_are_nearly_identical（T015未修正時）
    └─ 停止後の自動復旧ロジックなし
```

---

## [T010] IATF動画生成：VoiceVoxコンテナフリーズによるバッチ停止 (2026-05-09)

**症状**: IATF動画生成バッチが「箇条8.6.3 外観検査項目の管理」のTTS（音声合成）フェーズで完全に停止。`generation.log` にエラーは記録されず、17:09 以降更新が止まっていた。

**根本原因**:

- **コンテナの状態**: `clawstack-unified-voicevox-1` コンテナは「Up」状態であったが、内部プロセスがハングし、外部からの HTTP リクエストに応答しない状態になっていた。
- **監視の不備**: 既存の監視スクリプトは API の生存確認のみを行っており、TTS エンジンのハングを検知できていなかった。

**対策**:

1. **コンテナ再起動**: `docker restart clawstack-unified-voicevox-1` を実行し、正常レスポンスを確認。
2. **統合監視の導入**: `service_guardian.py` を新規作成。VoiceVox, Postgres, LiteLLM の L3/L4 ヘルスチェックを行い、異常時に自動再起動する機能を実装。

## [T011] IATF動画生成：QA不合格（Wチェック）の教訓の再利用ルール (2026-05-09)

**事象**: Wチェック（Gemini等）で指摘された不合格理由が、その動画の再生成には活かされるが、将来の別の動画生成には引き継がれず、同じミスを繰り返すリスクがあった。

**対策**:

1. **ナレッジ蓄積**: 不合格理由を `iatf_generation_lessons.json` に教訓として自動保存。
2. **ナレッジ注入**: 次回の動画生成時に、過去の全教訓をプロンプトへ自動的に「注意事項」として追加する仕組みを実装。
3. **DB記録**: Postgres DB に `qa_score` と `qa_feedback` を保存し、品質の経時変化を追跡可能にした。

---

## [T012] IATF動画生成：3Dキャラ透明化・重複・QAゲート形骸化 (2026-05-09)

**事象**: 生成された3D動画において、キャラクターが半透明になる、あるいは同じ場所に複数人が重複して出現する不備が発生。既存の Visual QA（統計的数値チェック）がこれを「合格」と判定し、不適合品が流出した。

**根本原因**:

- **QAの形骸化**: 従来の Visual QA は Pillow によるエッジ量・コントラスト計算のみを行っており、「画像に何が映っているか（意味的整合性）」を判断できていなかった。
- **偽のAIレビュー**: 以前のシステムは画像認識機能を持たないテキストAI（DeepSeek-V3等）に画像URLを渡しており、実質的な視覚チェックが行われていなかった。
- **Blender設定不足**: モデルのマテリアル blend_method が不透明（OPAQUE）に強制されておらず、透過設定が意図せず有効になっていた。
- **インスタンス管理不全**: ショット切り替え時に古いキャラクターオブジェクトの削除が不完全で、重複が発生していた。

**対策（新ルール）**:

1. **マルチモーダルAI (Kimi K2.6) の導入**: `ai_visual_reviewer.py` を新規作成。画像の内容（透明度、重複、Tポーズ）を「目視」で判定し、NG時はプロセスを物理的にロックするゲートを構築。
2. **Blenderマテリアル強制固定**: 全モデルの全マテリアルに対し、スクリプトで `blend_method = 'OPAQUE'` を強制適用。
3. **クリーンアップの標準化**: 各ショットの生成開始時に、Mesh, Armature, Collection を全削除するルーチンを `blender_animator.py` に組み込み。
4. **環境変数の固定**: `IATF_VIDEO_SLIDE_REVIEW_MODE=ai_required` を `.env` に固定。

---

## [T017] 自動学習ダッシュボードの表示遅延およびキャッシュ固着不具合 (2026-05-26)

**事象**: `http://localhost:8088/apps/growth_dashboard/index.html` にて、2026-05-24 の新規学習実績が「0件」と表示されていた。実際には裏側で 94 件の新規学習に成功していたが、ダッシュボード画面に反映されていなかった。また、手動でファイルを更新してもブラウザキャッシュの固着によって23日時点の古い表示が維持され続けた。

**根本原因**:

- **同期処理の設計漏れ**: 自動学習プログラム `universal_growth_daemon.py` 内で、画面用統計JSONファイル (`growth_stats.json`) の出力関数 `export_stats_json()` が起動時に一度だけしか実行されておらず、周期的な自動学習ループ (`while True`) 内から完全に漏れていた。
- **プロセスの不意の停止**: 5月25日 09:58頃にOS一時エラー (`[Errno 22] Invalid argument`) が発生した際、例外はキャッチされてログ出力されたものの、コンソールセッションの終了に伴いプロセス自体がサイレントに終了（ハングアウト）してしまっていた。
- **クライアント側キャッシュの固着**: `index.html` 内の `fetch('growth_stats.json')` 処理にキャッシュバスター（クエリパラメータ）が設定されていなかったため、Webブラウザが静的ファイルをキャッシュし続け、データの更新を検知できなかった。

**対策**:

1. **デーモンコードの修正**:
   `universal_growth_daemon.py` の `while True` 内に `export_stats_json()` を追加。15分おきの学習サイクルごとに統計JSONが自動再ビルドされるように修正した。
2. **キャッシュバスターの実装**:
   `index.html` の `fetch` リクエストにタイムスタンプを付与し、強制的に常に最新ファイルを取得するよう改善した：
   `const res = await fetch('growth_stats.json?t=' + new Date().getTime());`
3. **プロセス再起動と手動同期**:
   手動で集計JSONを強制再ビルドし、デーモンをバックグラウンドプロセスとして再起動（復旧完了）。

**なぜなぜ分析**:

| Why | 観察事実 |
| --- | --- |
| ①なぜ24日の学習履歴が0件？ | 集計ファイル `growth_stats.json` が24日 09:00以降更新されていなかった |
| ②なぜ更新されない？ | `universal_growth_daemon.py` が25日 09:58以降停止しており、起動時しかJSONを更新しない設計だった |
| ③なぜ起動時のみ？ | ループ処理内で `export_stats_json()` を呼び出しておらず、設計時に起動時のみの処理と誤認した |
| ④なぜ手動で更新しても変わらない？ | ブラウザが古いJSONファイルをローカルキャッシュから読み込み続けた |
| ⑤なぜキャッシュを読み込む？ | 静的URLにクエリパラメータ等のキャッシュ破棄用コードが組み込まれていなかった |

**再発防止**:
- 集計デーモン開発時は、データの書き出し・同期処理を必ずループの最深部に埋め込み、定期実行を担保すること。
- SPAやAJAX/fetchで静的データ（JSON等）をロードする際は、必ず `?t=timestamp` 形式のキャッシュ無効化設計を標準採用すること。

---

## [T021] 各PCノード障害の長期間放置問題 (2026-06-04)

**事象:** 各パソコン（K10, G3, LAVIE, Dynabook）の問題（Gmail sync一時フォルダによるディスク枯渇、Ollama負荷によるDynabook熱暴走、Docker/WSL2フリーズに伴うLAVIE通信途絶、QA否決によるバッチジョブのハング）が、ダッシュボードやプロセス上で認識可能であったにもかかわらず、自律的に修復されず長期間放置されていた。

### 根本原因
1. **死活監視への過度な依存:** `monitor_agent`およびダッシュボードが「ポートが開いているか（Liveness: HTTP 200）」のみを確認しており、処理のハングアップやディスクフル、論理エラーを検知・自動修復（Watchdog）する設計になっていなかった。
2. **ハッピーパス指向の開発設計:** 不安定な一般PC（通信切断、スリープ、突然の再起動）をノードとする現実に対して、障害発生時にロールバックして即時停止するような脆弱なクローズドループになっていた。

### 対策 (再発防止)
| 項目 | 内容 |
|---|---|
| 監視の強化 | ディスク容量、バッチの最終ジョブ実行からの経過時間等のパラメーターを監視項目へ追加 |
| 自動復旧の常駐化 | 各PCのタスクスケジューラにスタートアップ自動起動バッチを登録・常駐化し、スリープを無効化 |
| 例外許容デプロイ | `autonomous_coder.py` に `--allow-offline` モードを導入し、サテライトがオフライン時もローカル改善とGitバックアップを継続、復帰時に非同期デプロイ |
| 意味ゲート | 毎回の実行前に「意味ゲート (Meaning Gate)」で北極星目標との整合性を自動監査する |
| 記録 | INC-095, `universal_growth.db` (Record ID: 3054) |

---

## [T022] 2026-06-05 AIエージェントによるシステムの重複構築リスク（車輪の再発明）

**事象:** トラブル分析結果を記録するよう指示されたAIエージェントが、既存の正式な記録システム（`memory/trouble_history.md` や `incident_extract_for_fmea.json`）が既に存在しているにも関わらず、ワークスペース全体を十分に調査・検索せず、新規に `Failure_Analysis_20260605.md` という重複ファイルを作成する提案（実装計画）を行った。

**根本原因:**
* エージェントが新規タスクを受けた際、「類似の既存システムがないか」を網羅的に検索（ファイル一覧や内容の慎重な吟味）するステップをスキップし、即座に新規構築に走ったため。

**対策:**
* 自動処理エージェントやAIアシスタントは、新たなデータベースや管理用ファイルを作成する前に、必ず既存システム（過去トラや運用ルールなど）を検索し、重複を避けるルールを関連MDファイルに明記した。

---

## [T023] 2026-06-05 YouTube解析ダッシュボードの表示同期不備 (JSON vs DB)

**事象:** `iatf_youtube_monitor.py` が動画解析に成功し SQLite (`universal_growth.db`) へデータを保存していたが、ダッシュボード画面では表示が増えなかった。
**根本原因:** ダッシュボードがDBではなく静的なダミーデータを含む `iatf_youtube_summary.json` を直接読み込む設計になっており、DBからJSONへのエクスポート処理が漏れていた。
**対策:** `export_knowledge_history.py` 内に、DBから最新のYouTubeレコードを抽出し `iatf_youtube_summary.json` へ書き出すエクスポートロジックを追加し、定期同期ループに組み込んだ。

---

## [T024] 2026-06-05 K10 リソース過負荷による Ollama タイムアウト

**事象:** K10上でYouTube動画の文字起こしとOllama（Qwen3:8b）によるAI要約を並行実行した際、K10のCPU使用率が100%に張り付き、Ollamaの推論APIがタイムアウトエラーを起こした。
**根本原因:** K10はシステム全体を統括する「頭脳ノード」であり、重い推論処理を無制限に走らせると他のオーケストレーション機能に影響が出る。
**対策:** ノード負荷監視を強化し、K10でのLLM推論時はAPIのスロットリング・タイムアウト上限を設ける。重い計算処理は「筋肉ノード」であるLavie等へオフロードする設計（`cae_workload_router.yaml`）を厳守する。

---

## [T025] 2026-06-05 Paperless-ngx 連携パスの相違（Consumeフォルダ不一致）

**事象:** Scribdから自動ダウンロードしたPDF資料が、Paperlessのダッシュボードに反映されなかった。
**根本原因:** `scribd_ingestion.py` がファイルを独自の `data/scribd_downloads` に保存しただけで処理を終了していた。Paperless-ngxが自動取り込みを行う `paperless/consume` フォルダへの移動処理が欠落していた。
**対策:** ダウンロード完了後、ファイルを速やかに `paperless/consume` フォルダへコピーする連携フローをスクリプトに実装。

---

## [T026] 2026-06-05 GitHub巨大ZIP解凍時の Windows MAX_PATH エラー

**事象:** Github HarvesterがJavaベースの `industry4.0-mes_master.zip` をダウンロード後、解凍処理においてエラーが発生しクラッシュした。
**根本原因:** Javaアプリはフォルダ階層が深く、デフォルトの深いパス内で解凍しようとしたため、Windowsの最大パス長制限（260文字: MAX_PATH）を超過した。
**対策:** ZIP解凍などの外部ファイル処理は、浅いテンポラリフォルダ内で実行し、必要なファイルだけを移動する仕様に変更。

---

## [T027] 2026-06-05 Python SQLite `conn.close()` 順序ミスによるクラッシュ

**事象:** `export_knowledge_history.py` への追記実装中、`sqlite3.ProgrammingError: Cannot operate on a closed database.` エラーが発生した。
**根本原因:** 既存の `conn.close()` の後に、新規のデータ抽出用クエリを挿入してしまったため。
**対策:** データベースコネクションのクローズは、全抽出処理が完了しJSON書き出しを行う直前まで引き下げるようロジックを修正。

---

## [T028] 2026-06-05 ダッシュボードのK10 CPU使用率が常に0%になる不具合

**事象:** ダッシュボード上でK10のCPU使用率が常に0%と表示されていた。
**根本原因:** CPU使用率を取得する `monitor_agent.py` 内で、古い `wmic` コマンドが使用されていた。最新のWindows 11では `wmic` が廃止・削除されているため、裏側でコマンドエラーが発生し、例外処理によって常に `0.0` が返却されていた。
**対策:** CPU取得ロジックを最新のPowerShellコマンド（`Get-CimInstance Win32_Processor`）に書き換え、エージェントを再起動して復旧した。

---

## [T029] 2026-06-07 K10 monitor_agent CPU温度誤報告（LHM連携失敗）

**対象:** K10 NUCBOX_K10 / i9-13900HK / `scripts/monitor_agent.py` / LibreHardwareMonitor `:8085`

### 失敗の経緯（3段階）

| 段階 | 症状 | ユーザー確認値 |
|------|------|----------------|
| **F1** | `monitor_agent` 再起動直後 | `cpu_temp_celsius: 27.9`, `temp_source: fallback`, LHM 項目すべて空 |
| **F2** | LHM 起動後も `:8085` 未応答 | `Invoke-WebRequest http://127.0.0.1:8085/data.json` -> **接続できません** |
| **F3** | LHM HTTP 200 後もパース失敗 | `lhm_ok: False`, `lhm_error: no_cpu_temperatures_in_json`, 依然 fallback 27.9°C |
| **成功** | パーサ修正 + LHM Run 後 | `8085` 200 / 76376 bytes, `lhm_http`, CPU Package **84°C**, Core Max **85°C**, KIOXIA **99.2%** disk warning |

### 根本原因

1. **起動順序:** `monitor_agent` は LHM Remote Web Server より先に起動可能。8085 が死んでいる間は WMI/ACPI fallback のみ。
2. **fallback 誤値:** Windows ACPI サーマルゾーンは **27.9°C 等の非物理値**を返す。i9 実測 84–86°C と乖離。**fallback を CPU 温度として表示してはならない**（K10）。
3. **JSON スキーマ不一致:** LHM `data.json` は `SensorType` ではなく **`Type: "Temperature"`**。`Value` は **`"86.0 °C"` 文字列**（数値 float ではない）。旧パーサは `isinstance(val, float)` のみ -> 温度 0 件 -> `no_cpu_temperatures_in_json`。

### 対策（実装済み）

| # | 対策 | 場所 |
|---|------|------|
| 1 | LHM HTTP 読取 (`get_lhm_metrics`) を最優先 | `scripts/monitor_agent.py` |
| 2 | `Type` / `SensorId` / 文字列 `Value`・`RawValue` パース | 同上 `_lhm_parse_number`, `_lhm_walk_sensors` |
| 3 | `/metrics` に `lhm_ok`, `lhm_error`, `temp_source`, `cpu_package_c`, `core_max_c`, `disk_warnings` | 同上 |
| 4 | 運用 SOP: **LHM Run (8085) -> 8085 確認 -> monitor_agent 再起動** | `docs/troubleshooting/k10_lhm_monitor_agent_20260607.md` |

### 再発防止ルール

- K10 で `temp_source != lhm_http` のとき **CPU 温度をダッシュボード/サーマル制御の根拠に使わない**。
- CAE 重負荷前に `disk_warnings`（E: 99% 等）を確認。
- LHM はログオン時自動起動 + Remote Web Server Run をタスクスケジューラ化（未実装 -> follow-up）。

**記録:** INC-096, ByteRover `bd remember --key k10-lhm-monitor-inc096`, `docs/troubleshooting/fleet_lhm_monitor_agent_runbook.md`

---

## [T030] 2026-06-07 G3 monitor_agent 27.9°C fallback（LAVIE 再接続時と同型）

**対象:** G3 NucBoxG3_Plus / ユーザー `yns` / リポジトリなし

**症状:** Dashboard 27.9°C, `temp_source` 空, `lhm_ok` 空 → 8123 版導入後 `lhm_error: WinError 10061` → LHM GUI Run 後 **63°C lhm_http**

**G3 固有失敗:**

| # | 失敗 | 対策 |
|---|------|------|
| 1 | `D:\Clawdbot_Docker_20260125\scripts\*.ps1` 不存在 | K10 `:8123` から `lhm_setup.ps1` / `monitor_agent.py` を取得 |
| 2 | `:8112/monitor_agent.py` 旧版 | **`:8123` のみ使用** |
| 3 | LHM プロセス稼働中も 8085 拒否 | Options -> Remote Web Server -> **Run**（自動化不可） |

**成功:** `lhm_ok: True`, CPU Package 63°C, サーマル制御フィールドあり（80°C 以上で powercfg 制限）

**LAVIE/red_lavie  tonight:** 同一手順 — `docs/troubleshooting/fleet_lhm_monitor_agent_runbook.md`
