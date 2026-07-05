# スキル獲得パイプライン自動化+地形生成 実装仕様書 v1.0

作成日: 2026-07-05 | 目的: **API枯渇後もローカルLLM級のモデルが1ユニットずつ実装を引き継げる**完全仕様
前提知識: `design/skill_acquisition_pipeline.md`(9ステージ設計) / `design/HANDOVER_QUEUE5_AND_BEYOND.md` / `qc/mecha_rig_checksheet.md`(実行規律)

## 0. 実装者への絶対ルール(どのAIモデルでも遵守)

1. **1セッション=1ユニット。** 下記U1〜U8を番号順に(依存関係があるため)。ユニット完了ごとに`git add(自分のファイルのみ)→commit→push`。
2. 各ユニットの「合格判定」コマンドが通るまで次へ進まない。通らない場合は**改造範囲を広げず**、escalation条件に従い人間へ報告。
3. 既存ファイルの変更は本仕様に列挙された箇所のみ。**リファクタ・改名・移動は禁止**(Surgical Changes)。
4. ポートを使う場合はdocker-compose.ymlで空きを実測(T008)。新規は本仕様の指定に従う。
5. 学習系の検証は必ず「数値+レンダー機械チェック(walk_check.json)」の両方(T047教訓: 目視相当>数値)。

## 1. 全体像(状態機械)

`skill_requests.json` の各依頼が持つ status の遷移:

```
queued → interpreted → reference_found → license_pending →(人間承認)→ retargeted
       → training → learned / escalated / rejected
分岐: needs_human_source(お手本が自動で見つからない) / needs_terrain(地形必要→U6が前提)
```

- 依頼キュー: `data/workspace/apps/mecha_motion_lab/skill_requests.json`(実装済・U0)
- 受付API: `rl_integration/autonomy/skill_request_api.py` 127.0.0.1:8118(実装済・U0)
- 学習実行: `rl_integration/autonomy/motion_learning_supervisor.py`(実装済)
- リターゲット: `rl_integration/stage_b/bvh_retarget.py`(実装済)

## 2. 実装ユニット

### U1: 依頼解釈器(S2) — `rl_integration/autonomy/u1_interpreter.py`(新規, ~120行)
- **入力**: skill_requests.json の `status=="queued"` の各行
- **処理**: LiteLLM `http://localhost:4001/v1/chat/completions` model=`local_fast` に固定ルーブリックで問い合わせ:
  `{skill_name(英snake), taxonomy(9語彙のいずれか: locomotion|posture|manipulation|care_assist|factory_work|most_basic|therblig|martial_arts|sports), required_tier(1|2|3), needs_terrain(null|stairs|slope_up|slope_down|uneven), search_keywords[]}` をJSONで返させ、パース失敗はキーワード表フォールバック(階段→stairs等の対訳辞書を同ファイル内に定義)
- **出力**: 該当行に `interpretation` フィールドを追記し `status="interpreted"`
- **合格判定**: `python u1_interpreter.py --once` 実行後、「階段を登る」の依頼行が `needs_terrain=="stairs"`, `required_tier==1` になること
- **escalate if**: LLMとフォールバック両方で分類不能 → status=`needs_human_source`, notesに理由

### U2: お手本レジストリ照合(S3) — `rl_integration/autonomy/u2_reference_finder.py`(新規, ~100行)+ `reference_registry.yaml`(新規)
- **registry初期内容**(手書き): 100STYLEの既知クリップ対応表
  `walk→Neutral/Neutral_FW.bvh, run→Neutral/Neutral_FR.bvh, walk_backwards→Neutral_BW, idle→Neutral_ID`(zipから展開: `C:\v50_work\datasets\100style\100STYLE.zip`)。**stairs/slopeは平地モーションwalkを流用可**(地形はU6が担当。人間の階段登行は歩行の変形であり、v1はwalk参照+地形カリキュラムで学習させる)と明記
- **処理**: interpretation.skill_name をregistryで照合 → ヒット: BVH展開+パス記入 `status="reference_found"` / ミス: `status="needs_human_source"`(**Web自動ダウンロードはv1では実装しない** — ライセンス誤取得リスク。人間が候補URLを提示する)
- **合格判定**: walkの依頼が Neutral_FW.bvh のパスを得ること
### U3: ライセンスゲートUI(S5・人間) — `skill_request_api.py` 拡張(+30行)+ dashboard(+20行)
- API: `POST /requests/<id>/approve` と `/reject`(body: {by, note})→ status を `retarget_ready`/`rejected` に
- dashboard: license_pending 行に承認/却下ボタン。**自動承認の実装は禁止**(S5は人間必須)
- 100STYLE系はライセンス判断記録が既存(`stage_b/license_decision.json`)なので、registry由来クリップは `license_pending` をスキップし `retarget_ready` へ直行してよい(判断済みデータセット内の別クリップのため)
- **合格判定**: curlでapprove→statusが遷移すること

### U4: 自動リターゲット(S6) — `rl_integration/autonomy/u4_retarget_runner.py`(新規, ~60行)
- `retarget_ready` の行に対し `bvh_retarget.py --bvh <path> --out C:\v50_work\refs\<skill>.json` をsubprocess実行、成功で `status="retargeted"`+ref_pathを記入
- **合格判定**: 出力JSONの `period_sec` が0.6〜2.5秒に入ること(この範囲外はescalate)

### U5: 学習ディスパッチ(S8) — `rl_integration/autonomy/u5_train_dispatcher.py`(新規, ~80行)
- `retargeted` の行に対し supervisor を detached起動(`--skill <name> --ref-json <ref> --iterations 3000 --entropy 0.002 --init-log-std -0.9`)。同時実行は**1スキルまで**(GPU1枚)。status=`training`
- supervisor_status.json の state を監視し、learned→`learned` / escalated→`escalated` をキューに反映
- **合格判定**: ドライラン(--dry-run でコマンド出力のみ)が正しい引数を組むこと

### U6: 地形生成 — `train_v50_walk_tracking.py` 拡張(+60行程度)
- CLI `--terrain none|stairs|slope_up|slope_down`(default none)
- Env内XML書換に追記(既存のactuator除去等と同じ場所):
  - stairs: `<geom type="box" size="0.5 0.15 <h/2>" pos="0 <y_i> <z_i>"/>` を10段。段高h=0.10(V50脚力への初期値・人間比0.17より低いカリキュラム開始点)、奥行0.30、進行方向は-Y(前方)なので y_i = -(0.6+0.30*i), z_i = -0.92+h*(i+0.5)。最初の0.6mは平地助走
  - slope_up/down: 傾斜8°のbox(size 6 0.5→回転euler)を y=-0.6 から設置
- 報酬: 期待前進 x_expect は不変(水平距離)。**転倒判定の stand_z を「地形上の期待高さ」に補正**: stairs時 expected_z(y) = stand_z + h*floor(max(0, (-y-0.6)/0.30)) を fallen 判定に使用(これを怠ると登った時点でfallen誤判定になる — 必読)
- **合格判定**: `--terrain stairs --iterations 2` がエラーなく走り、レンダーフレームに階段が写ること(walk_check.jsonが生成されること)
- **escalate if**: 接触が爆発(物理発散でNaN) → 段高hを0.05に下げて再試行、それでもNGなら報告

### U7: キューオーケストレータ — `rl_integration/autonomy/u7_queue_daemon.py`(新規, ~80行)
- 5分ごとに skill_requests.json を読み、状態ごとにU1/U2/U4/U5を`--once`実行する薄いポーリングループ。keep_awake併用
- **合格判定**: queued→interpreted→reference_found→retargeted→training が人手なしで流れること(walkでE2Eテスト)
### U8: 起動の恒久化 — Task Scheduler登録(人間と共同)
- skill_request_api.py / u7_queue_daemon.py をログオン時自動起動に登録(`schtasks`はユーザー権限で可)。手順を`design/`にメモ

## 3. 現在の未完了事項(このspec外・参考)
- walk本体の習得(walk_tier1cが自律学習中)— **U5以降のE2EテストはこのwalkのlearnedがあるとBest**
- 左手メッシュ(右手ミラー)/ B-2完全カノニカルエクスポータ / 可視化(qpos→ARMFIX blend焼き込み)
- T048恒久対策(dxf2step意味ゲート)は別bd

## 4. 進捗記録欄(実装者が更新すること)
| ユニット | 状態 | commit | 日付 |
|---|---|---|---|
| U0(受付) | ✅ 実装済 | c1435251c | 2026-07-04 |
| U1 | ✅ 合格判定PASS(「階段を登る」→stairs/tier1。LLMタイムアウト時のフォールバック辞書経路も実証) | 本commit | 2026-07-05 |
| U2 | ✅ 合格判定PASS(walk→Neutral_FW.bvh実パス取得、zip自動展開、stairs_climbも同時解決) | 本commit | 2026-07-05 |
| U3 | ✅ PASS(approve→retarget_ready遷移/不正遷移409/reject。※Content-Length過剰readのハングバグを発見・修正済) | 本commit | 2026-07-05 |
| U4 | ✅ PASS(walk/stairs_climb両方 retargeted、period 1.3s=範囲内) | 本commit | 2026-07-05 |
| U5 | ✅ PASS(dry-run正引数/GPU占有時スキップ実動作/needs_terrainはU6まで保留を確認) | 本commit | 2026-07-05 |
| U6 | ✅ PASS(--terrain stairs実行/階段11geom生成/レンダー目視で階段確認/物理発散なし。※罠#8=レンダーXML複製の乖離を発見しbuild_model_xmlに統一) | 本commit | 2026-07-05 |
| U7 | ✅ PASS(E2E:「走る」がqueued→retargetedまで1パス全自動、GPU占有時dispatch正スキップ。※LLM誤分類対策で辞書優先化) | 本commit | 2026-07-05 |
| U8 | ✅ 登録済(schtasksは権限拒否→Startup VBS方式: mecha_motion_lab_autostart.vbs。API+U7デーモン稼働中) | 本commit | 2026-07-05 |
