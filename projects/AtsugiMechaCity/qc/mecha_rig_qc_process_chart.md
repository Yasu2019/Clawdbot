# メカ・リギング QC工程表 (Mecha Rig QC Process Chart) v1.0

作成日: 2026-07-03 | 根拠: INC-140/[T046]・[T044]・[T035]・[T033]の実修復作業
対象: PartPacker等で生成した3Dメカモデルをリギングし、歩行プレビューを出すまでの全工程
想定実行者: **ローカルAIモデル(低能力でも可)**。判断が必要な箇所は必ず人間へエスカレーション。

## 実行者への絶対ルール（工程より先に読むこと）

1. **各工程のコマンドをそのまま実行し、数値基準と比較するだけでよい。** 基準を満たさない場合は**停止して報告**。自分で修理方法を発明しない。
2. **ゲートの許容値・閾値を緩めることは禁止**（緩和は人間承認+正解基準での校正記録が必須。[T035]/INC-140で2回false-PASS事故）。
3. **オリジナル(KEEP_ORIGINAL)ファイルの上書き・移動・削除は禁止。**
4. 編集系工程の前に**必ずバックアップコピーを作成**（工程0）。
5. オブジェクト配置は **`matrix_world` 経由のみ**。`obj.scale`/`obj.location` への直接代入は禁止（親子空間/depsgraph事故の実績あり）。
6. 数値がPASSでも**目視工程(工程7・10)は省略禁止**。「数値ゲートは見える破綻を保証しない」([T035])。

## 環境定数

| 名前 | 値 |
|---|---|
| BLENDER | `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`（`-b`必須） |
| PYTHON | `D:\Clawdbot_Docker_20260125\.venv\Scripts\python.exe`（cv2/numpy入り） |
| TOOLS | `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\inc140_repair\` |
| GATE | `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\v50_joint_attachment_gate.py` |
| PREVIEW | `D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\v50_final_walk_preview.py` |
| ORIG(正解) | `D:\AI\PartPacker\output\KEEP_ORIGINAL_..._v50_BASELINE\robot_walk.blend`（機体ごとに指定） |
| 作業出力 | `C:\v50_work\`（D:満杯対策。D:空き<20GならC:へ） |

## 工程表

| # | 工程 | 作業内容 | 管理項目(何を測る) | 管理基準(合格値) | 方法/コマンド | NG時処置 | 記録 |
|---|---|---|---|---|---|---|---|
| 0 | バックアップ | 編集対象blendを `*.PRE_<工程名>_BACKUP_<日付>.blend` にコピー | バックアップ存在 | コピー後にファイルサイズ一致 | `cp -n src dst; ls -la` | 停止・報告 | パスを作業ログへ |
| 1 | 溶接検査 | 全メッシュの境界エッジ/島数を計測 | `boundary_edges / faces` | **< 0.5**（≥0.5は未溶接） | `BLENDER -b <blend> -P TOOLS\v50_mesh_inspect.py` | 工程2へ | inspect JSON保存 |
| 2 | 溶接実施 | 未溶接メッシュにMerge by Distance(最大寸法×0.05〜0.1%)+法線再計算 | 溶接後の島数・非多様体 | 島数 **≤2**、nonmanifold **≤10** | `BLENDER -b <src> -P TOOLS\v50_weld_apply.py -- --input <src> --output <dst> --report <json>` | 停止・報告（メッシュ再生成領域） | weld report JSON |
| 3 | 正解ダンプ | ORIGの全メッシュworld行列/中心/寸法をJSON化 | ダンプ件数 | ORIGのメッシュ数と一致 | `BLENDER -b ORIG -P TOOLS\dump_orig_matrices.py -- --input ORIG --out orig_matrices.json` | 停止・報告 | orig_matrices.json |
| 4 | 全身復元 | **全メッシュ**(Ground除く)をORIG行列へ復元+**全アーマチュア**の腕ボーン/マーカーをORIGのSHARED_CORE位置へ | 部分復元禁止 | WARN出力ゼロ | `BLENDER -b <src> -P TOOLS\v50_arm_reattach.py -- --input <src> --orig-json <json> --output <dst>` | WARNのメッシュ名を報告 | armfix ログ |
| 5 | 寸法照合 | 復元後の全体バウンディングをORIGと比較 | 幅X/高さZ/奥行Y | 各 **ORIG±1%以内** | `BLENDER -b <dst> -P TOOLS\diff_vs_orig.py -- --input <dst> --orig <json>`(BODY_BOUNDS行) | 停止・差分上位を報告 | diff出力 |
| 6 | 変位照合 | 全メッシュのORIGとの中心距離 | 最大変位(意図した部品以外) | **< 0.05**（マーカー/プロキシ/CORE除く） | 同上(displacement top行) | 変位リスト報告 | 同上 |
| 7 | 静止目視 | 正面+側面フルボディスナップショット | 目視: 四肢接合/浮遊破片/埋没部品/膝パッド類の突出 | ORIG画像と並べて差が説明可能 | `BLENDER -b <dst> -P <snapshot script>` → 画像をORIG画像と比較 | 停止・両画像を人間へ提出 | PNG 2枚 |
| 8 | 歩行レンダー | 180フレーム歩行プレビュー生成 | フレーム数/ffmpeg | Saved=180, ffmpeg_returncode=0, **巨大オブジェクト無し**(目視1フレーム) | `BLENDER -b -P PREVIEW -- --blend <dst> --out-dir <out> --frames 180` | 停止・フレーム画像を報告 | mp4+report JSON |
| 9 | 接合ゲート | 強化版ゲート実行（許容値はデフォルトのまま） | verdict / failed_joints | **PASS_JOINT_ATTACHMENT / 空** | `BLENDER -b -P GATE -- --blend <out>\v50_final_walk_preview.blend --out <json>` | 停止・失敗関節と数値を報告（**許容値変更禁止**） | gate JSON |
| 10 | 動画目視+比較ゲート | フレーム3点(1/90/180)目視+original compare gate | component比 / 目視破綻 | component比 **< 1.75**、四肢接合を目視確認 | `PYTHON v50_original_compare_gate.py --baseline <mp4> --candidate <mp4> --out <json>` | 停止・数値と画像を報告 | compare JSON |
| 11 | 人間検収 | 画像をTelegram等でユーザーへ提示 | ユーザー承認 | 明示的OK | sendPhoto(既存パターン) | 指摘内容を工程6の差分照合で検証([T046]教訓7) | message_id |
| 12 | 記録・保全 | trouble_history追記+成果物をリポジトリへ+commit/push | push成功 | `git status`=up to date | git add(自分のファイルのみ)/commit/push | 停止・報告 | commit hash |

## エスカレーション基準（人間の判断が必要）

- 工程2でNG（メッシュ自体の破損=再生成判断）
- 工程9で失敗（ゲート校正 or 形状修理の判断。**実行者が許容値を触るのは禁止**）
- 工程11でユーザー指摘（→差分照合の結果を添えて報告）
- ORIGが存在しない機体（正解基準の決定は人間）

関連: FMEA=`mecha_rig_fmea.md` / チェックシート=`mecha_rig_checksheet.md` / 30体展開設計=`docs/troubleshooting/fable5_mecha_multirobot_scaleup_decision_20260703.md`
