# メカ・リギング チェックシート v1.0（ローカルAI実行用）

対象機体: ________  実行日: ________  実行者(モデル名): ________
使い方: **上から順に実行。1項目=1コマンド。[実測]欄に数値を書き、基準と比較して✅/❌。❌が出たら即停止し、このシートごと人間へ報告。修理の即興は禁止。**

環境定数は `mecha_rig_qc_process_chart.md` の表を使うこと。
以下、`<SRC>`=対象blend、`<ORIG>`=正解blend、`<W>`=作業ディレクトリ(C:\v50_work等)。

## Phase 0: 前提確認

| ✓ | 項目 | コマンド | 合格基準 | 実測 |
|---|---|---|---|---|
| ☐ | D:空き容量 | `df -h /d` | 空き **≥20G**（未満なら出力先をC:に変更して続行） | ___G |
| ☐ | ORIG存在・読取専用扱い確認 | `ls -la <ORIG>` | ファイル存在（**このファイルへの書込みコマンドは以後一切禁止**） | ☐ |
| ☐ | バックアップ作成 | `cp -n <SRC> <SRC>.PRE_QC_BACKUP_$(date +%Y%m%d).blend` | コピー後ファイルサイズが<SRC>と一致 | ☐ |

## Phase 1: 溶接（FMEA #1）

| ✓ | 項目 | コマンド | 合格基準 | 実測 |
|---|---|---|---|---|
| ☐ | 溶接検査 | `BLENDER -b <SRC> -P TOOLS\v50_weld_apply.py -- --input <SRC> --output <W>\welded.blend --report <W>\weld.json` | 実行exit=0 | ☐ |
| ☐ | 溶接結果 | `<W>\weld.json` を読む | 各WELDED行: boundary後値 **< boundary前値×0.05** かつ nonman **≤10** | ___ |
| ☐ | 溶接対象ゼロの場合 | WELDED_COUNT=0 なら | そのまま `<W>\welded.blend` を次工程へ（正常） | ☐ |

## Phase 2: 正解復元（FMEA #4, #5）

| ✓ | 項目 | コマンド | 合格基準 | 実測 |
|---|---|---|---|---|
| ☐ | 正解ダンプ | `BLENDER -b <ORIG> -P TOOLS\dump_orig_matrices.py -- --input <ORIG> --out <W>\orig_matrices.json` | `DUMPED <N> objects` のNがORIGメッシュ数と一致 | N=___ |
| ☐ | 全身復元 | `BLENDER -b <W>\welded.blend -P TOOLS\v50_arm_reattach.py -- --input <W>\welded.blend --orig-json <W>\orig_matrices.json --output <W>\restored.blend` | 出力に `WARN` が**1件もない** / `ARMATURE`行が**対象ボーンを持つ全アーマチュア分**出ている | WARN=___件 |
| ☐ | 寸法照合 | `BLENDER -b <W>\restored.blend -P TOOLS\diff_vs_orig.py -- --input <W>\restored.blend --orig <W>\orig_matrices.json` | BODY_BOUNDSのsize 3値がORIGと**各±1%以内** | ___ |
| ☐ | 変位照合 | 同上出力のdisplacement top | マーカー/プロキシ/SHARED_CORE**以外**の最大変位 **< 0.05** | max=___ |
| ☐ | 欠落部品 | 同上出力 | `MISSING vs orig: []`（空リスト） | ☐ |

## Phase 3: 静止目視（FMEA #9, #14 — 省略禁止）

| ✓ | 項目 | コマンド | 合格基準 | 実測 |
|---|---|---|---|---|
| ☐ | スナップショット | `BLENDER -b -P TOOLS\v50_fullbody_snapshot.py -- --input <W>\restored.blend --outdir <W>` | `fullbody_front.png` / `fullbody_side.png` 生成 | ☐ |
| ☐ | 全身が映っているか | front画像を見る | **頭と両足が両方**画像内にある(見切れなし) | ☐ |
| ☐ | 四肢接合 | front画像を見る | 腕2本が肩に、脚2本が骨盤に接続。**空中に浮く破片ゼロ** | ☐ |
| ☐ | 突出部品 | front/side画像をORIGの同アングル画像と並べる | ORIGにある突出部品(膝パッド等)が候補にもある | ☐ |
| ☐ | 巨大異物 | 両画像 | ロボット以外の巨大な球/柱が**ない**（FMEA #6） | ☐ |

## Phase 4: 歩行レンダー+ゲート（FMEA #2, #3, #8）

| ✓ | 項目 | コマンド | 合格基準 | 実測 |
|---|---|---|---|---|
| ☐ | 180fレンダー | `BLENDER -b -P PREVIEW -- --blend <W>\restored.blend --out-dir <W>\preview --frames 180` | `Saved:`が180回 / ffmpeg_returncode=0 | ___ |
| ☐ | フレーム目視 | frame_0001 / 0090 / 0180 を見る | 全身が映る・四肢接合・巨大異物なし | ☐ |
| ☐ | 接合ゲート | `BLENDER -b -P GATE -- --blend <W>\preview\v50_final_walk_preview.blend --out <W>\gate.json` | verdict = **PASS_JOINT_ATTACHMENT** / failed_joints = **[]** | ___ |
| ☐ | ゲート健全性 | `<W>\gate.json` の全関節 | `rest_pair_distance` に **>1.0 の異常値がない**（あれば測定バグFMEA#8、結果無効で報告） | max=___ |
| ☐ | **禁止確認** | — | このPhaseで `--rest-ratio`/`--attach-ratio` 等の**引数を追加していない**こと | ☐ |

## Phase 5: 比較+人間検収（FMEA #14）

| ✓ | 項目 | コマンド | 合格基準 | 実測 |
|---|---|---|---|---|
| ☐ | 比較ゲート | `PYTHON v50_original_compare_gate.py --baseline <ORIG mp4> --candidate <W>\preview\*.mp4 --out <W>\compare.json` | component_count比 **< 1.75**（他フラグは報告のみ） | 比=___ |
| ☐ | 人間検収 | 画像をユーザーへ送付(Telegram既存パターン) | ユーザーの明示OK。**指摘があれば工程Phase2の変位照合で検証してから回答** | ☐ |

## Phase 6: 記録（完了条件）

| ✓ | 項目 | 内容 |
|---|---|---|
| ☐ | trouble_history追記 | 新規問題があれば `data/workspace/memory/trouble_history.md` にT番号で追記+FMEAに行追加 |
| ☐ | 成果物保全 | gate.json / compare.json / スナップショットPNG を機体フォルダへコピー |
| ☐ | commit+push | 自分が変更したファイル**のみ** `git add` → commit → push → `git status` up to date |

## 停止・報告テンプレート（❌発生時にこのまま出力する）

```
[QC STOP REPORT]
機体: <名前>
停止Phase/項目: <番号と項目名>
コマンド: <実行したコマンド>
実測値: <値>  合格基準: <基準>
関連FMEA行: #<番号>
添付: <JSONパス/画像パス>
判断要請: この先の修理方針は人間の指示を待ちます。
```
