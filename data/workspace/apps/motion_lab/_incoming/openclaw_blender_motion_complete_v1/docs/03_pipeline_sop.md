# 03 実行パイプライン SOP

## Step 1 台本を動作タグへ分解
例：
「女の子が部屋に入り、少し驚いて、机の上の本を手に取り、カメラに向かって説明する」

分解：
- enter_room: walk_in
- surprise: surprised_reaction
- reach_book: reach / pick_up
- explain: talking + hand_gesture
- look_camera: head_track_camera

## Step 2 モーション候補表を作る
`samples/motion_plan_template.csv` に記入。

## Step 3 Mixamo/BVH/Rokokoから候補を取得
- 直接ダウンロードしたFBX/BVHを `assets/motions/raw` へ配置
- ライセンス情報を `assets/motions/licenses` へ保存

## Step 4 正規化
- fps統一
- root位置リセット
- スケール統一
- 不要な移動を削除または保持選択

## Step 5 リターゲット
- 標準ボーンマップを作る
- 対象キャラへ適用
- NLAクリップ化

## Step 6 品質チェック
- 足滑り
- 膝の逆曲がり
- 手のめり込み
- 視線方向
- 重心破綻
- カメラ外への逸脱

## Step 7 修正
- タイミング補正
- IK補正
- 手首/指/顔は手修正優先
- カット分割で破綻を隠す

## Step 8 レンダリング
- Eevee Next / Cyclesを用途で選択
- まず低解像度プレビュー
- 最終レンダリング前に全カットをチェック
