# FEM Impact 現状引継ぎ

更新日時: 2026-07-26 JST  
プロジェクト: `D:\Clawdbot_Docker_20260125`  
Beads: `Clawdbot_Docker_20260125-ffmr`

## 1. 現在の結論

- ThinkPadではDXF→3DとFEM Impactを1対1並列運用し、高負荷時だけ抑制する方針。
- FEM ImpactのTelegram進捗通知は、解析開始時と5%刻み（5～95%）で送る。
- 今後の進捗画像は上面図ではなく、薄板でも角度差が分かる`iso`斜視表示にする。
- 旧ジョブ`tri-thinkpad-fem_impact-24b3024a`は実行中ではない。
- 新規計算は、既存タスクをユーザー確認なしに止めないルールに従い、開始保留中。

## 2. 旧ジョブの確定状態

```text
job=tri-thinkpad-fem_impact-24b3024a
input=test_practical_doe01.in
case=/home/yasu/clawstack_satellite/impact_bundle/AUTO_FIX_ORIENTATION_20250804/Impact/160um_Panel_20250725/Rough_Mesh
end_time=0.0063
latest_vtk_time=0.002
progress=31.746%
running=false
sent=0,5,10,15,20,25,30
```

5～30%の各通知は、すべて同じ
`test_practical_doe01.in_surface_0.002000.vtk`を参照している。
したがって、それらの画像で解析形状・応力分布に変化がなかったのは、
解析結果が更新されていない同一VTKを繰り返し描画したためである。

状態ファイル:

`D:\Clawdbot_Docker_20260125\data\workspace\fem_impact_progress\tri-thinkpad-fem_impact-24b3024a.json`

## 3. 斜視表示の修正

修正コミット:

`c3a8d1755e fix(fem): render progress images from oblique view`

変更内容:

- `impact_vtk_to_png.py`へ`--camera iso`指定を追加。
- 薄板で上面図に見えないよう、XY面を回転させながらZを表す投影へ変更。
- `fem_impact_progress_telegram.py`から常に`--camera iso`を指定。
- 30%画像を同一VTKから斜視で再描画し、Telegramへ表示修正版を1回送信済み。
- 進捗の送信済み状態には再送分を追加せず、重複防止状態を維持。

対象ファイル:

- `D:\Clawdbot_Docker_20260125\scripts\impact_vtk_to_png.py`
- `D:\Clawdbot_Docker_20260125\scripts\fem_impact_progress_telegram.py`
- `D:\Clawdbot_Docker_20260125\docs\FEM_IMPACT_TELEGRAM_PROGRESS_RULE.md`

修正前バックアップ:

`D:\Clawdbot_Docker_20260125\backups\fem_progress_iso_20260726_041507`

## 4. 新規計算の準備状態

新規計算用に旧結果から分離したケースをThinkPad側へ準備済み。

```text
/home/yasu/clawstack_satellite/impact_bundle/AUTO_FIX_ORIENTATION_20250804/Impact/fresh_runs/fresh-doe01-20260726-0334/test_practical_doe01.in
```

入力の解析時間:

```text
run from 0.0 to 0.0063
```

ThinkPad側の一回限り実行キュー:

```text
/home/yasu/clawstack_satellite/data/work/fem_fresh_queue/fresh-doe01-20260726-0334/run.sh
```

同ディレクトリには`HOLD_FOR_USER_CONFIRMATION`があり、解除されるまで
新規ソルバーを開始しない。これは、古いタスクをユーザー確認なしに停止・削除・
置換しないグローバルルールを守るためである。

K10側の新規進捗モニター:

```text
PID=32052
process=python
start=2026-07-26 03:37:13 JST
```

モニターは`--wait-start-seconds 28800`でソルバー開始を待機する構成。
モニターだけが待機しており、HOLD中は新規FEM計算そのものは始まらない。

## 5. 次の担当者が行うこと

1. ユーザーから、現在の既存タスク完了後に新規FEM計算へ切り替えてよいか、
   明示確認を得る。
2. 許可が得られた場合だけ、ThinkPad側の
   `HOLD_FOR_USER_CONFIRMATION`を解除する。
3. 既存タスクを止める必要がある場合は、対象名・PID・影響を提示し、
   停止または削除について別途確認する。
4. 新規ソルバー開始後、0%通知と5%刻みの斜視画像がTelegramへ届くことを確認する。
5. 各通知が異なるVTK時刻を参照しているか確認する。同一VTKで複数段階を
   一括送信する挙動は避け、必要なら通知ロジックを追加修正する。
6. 100%は既存の最終成果物配信処理に任せ、進捗モニターは95%までとする。

## 6. 重要な運用ルール

ユーザーの現在指示に含まれない古いタスクが残っている場合:

1. 読み取り専用で状態を確認する。
2. 古いタスクの名前、状態、影響をユーザーへ提示する。
3. 停止・削除・置換について確認を得る。
4. 明示許可後にだけ古いタスクを処理し、新しいタスクを開始する。

進捗モニターはソルバーを停止、シグナル送信、reniceしてはならない。

## 7. 検証済み事項

- Python構文検査:
  `scripts/impact_vtk_to_png.py`および
  `scripts/fem_impact_progress_telegram.py`は合格。
- 上面図とiso斜視図を同一VTKで生成し、目視で明確な角度差を確認。
- Telegramへ30%斜視表示修正版を送信成功。
- 修正コミットはGitHubへpush済み。

## 8. 注意事項

- 斜視表示の変更はカメラ投影だけであり、解析値を変更しない。
- 旧ジョブが30%で終わった問題は、画像角度の問題とは別である。
- `0.002 / 0.0063 = 31.746%`で、利用可能な最終VTKが0.002だった。
- 新規解析開始の許可を得るまでは、HOLDを勝手に解除しない。
