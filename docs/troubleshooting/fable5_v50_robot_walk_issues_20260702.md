# Fable5相談用: V50 3Dロボット歩行・関節接合の現時点問題整理

作成日: 2026-07-02 JST  
対象: `projects/AtsugiMechaCity` V50 robot walk / armature / preview pipeline  
目的: Fable5に、現時点までの問題点・改善済み事項・未解決論点を相談するための共有メモ。

## 1. 現在の結論

V50は、関節接合ゲートとしては一度 `PASS_JOINT_ATTACHMENT` まで改善した。  
ただし、オリジナルV50との比較ゲートはまだ `REVIEW_REQUIRED` であり、Telegram送信・正式採用は止めている。

重要な現状:

- 肩・肘・手首・股・膝・足首の接合ゲート: PASS
- 180フレーム / 24fps / 7.5秒の動画生成: 成功
- オリジナルV50比較: REVIEW_REQUIRED
- 残る主問題: `candidate_has_more_large_disconnected_components_than_original`
- Telegram送信: 未実施
- オリジナルV50 baseline: 削除・上書きせず保持

## 2. 直近の成果物

最新候補:

- MP4: `scratch/v50_preview_shoulder_socket_180/v50_fullbody_normalized_final_walk_preview.mp4`
- preview blend: `scratch/v50_preview_shoulder_socket_180/v50_final_walk_preview.blend`
- joint gate report: `scratch/v50_preview_shoulder_socket_180/v50_joint_attachment_gate_report.json`
- original compare report: `scratch/v50_preview_shoulder_socket_180/v50_original_compare_gate_report.json`

基準動画:

- `D:\AI\PartPacker\output\KEEP_ORIGINAL_flow_big_parts_strict_pvae_20260628_025827_v50_BASELINE\robot_walk_v50_arm_chain_joint_core.mp4`

## 3. 改善済みの問題

### 3.1 動画長さの不一致

以前の候補は短尺で、オリジナルV50比較ゲートに不利だった。  
現在は候補も baseline も以下で揃えている。

- baseline frames: 180
- candidate frames: 180
- baseline fps: 24.0
- candidate fps: 24.0
- baseline duration: 7.5 sec
- candidate duration: 7.5 sec

### 3.2 診断用ジョイントロックが動画に映る問題

以前は、肩・肘・手首などの診断用ロック球/シリンダーが見えてしまい、動画の見た目が悪化していた。  
現在は `--show-joint-locks` を指定しない限り、診断用ロックは最終レンダーに出さない。

### 3.3 両肩の接合ゲートNG

以前は `shoulder_L` と `shoulder_R` が `parent_far_from_joint_at_rest` で失敗していた。  
原因は、骨格上は肩ピボットがあるが、胴体側の可視メッシュが肩ピボットに届いておらず、接触面が無かったこと。

対応:

- `v50_final_walk_preview.py` で `V50_RENDER_ShoulderSocket_L/R` を生成
- `v50_joint_attachment_gate.py` で肩ソケットを胴体側接触面として判定

結果:

- `PASS_JOINT_ATTACHMENT`
- failed joints: none

## 4. 現在残っている主問題

### 4.1 見た目上の分離コンポーネントが多い

最新の original compare gate:

```json
{
  "verdict": "REVIEW_REQUIRED",
  "visual_compare_score": 0.8875,
  "hard_flags": [],
  "soft_flags": [
    "candidate_has_more_large_disconnected_components_than_original"
  ]
}
```

比較指標:

| metric | baseline | candidate | ratio |
|---|---:|---:|---:|
| component_count | 1.03125 | 7.5 | 7.272727 |
| foreground_ratio | 0.104960 | 0.447196 | 4.260651 |
| edge_density | 0.013141 | 0.011060 | 0.841654 |
| motion_mean_absdiff | 0.012223 | 0.007283 | 0.595844 |
| duration | 7.5 sec | 7.5 sec | 1.0 |

解釈:

- 関節接合ゲートはPASSしているが、映像の二値化/連結成分上はオリジナルより分離パーツが多い。
- 手、腕の外装片、肩まわり、脚の外装片などが個別コンポーネントとして検出されている可能性が高い。
- hard flag は無いが、視覚品質としてはまだ正式送信レベルではない。

### 4.2 左手メッシュが安定していない

V50には安定した独立 `Hand_L` メッシュが無い。  
過去の分類では `geometry_0.005` は「Hand_Lに近いが、forearm-end meshなのでHand_Lへ奪ってはいけない」と扱われていた。

現対応:

- rigの意味上は `geometry_0.005` を `LowerArm_L` 側として扱う
- ただし `v50_joint_attachment_gate.py` では、左手首の可視接触面として `geometry_0.005` をQA用途だけに使う
- 不安定な `V50_PROXY_Hand_L_*` は最終レンダーから非表示

懸念:

- QA上はPASSするが、見た目として左手・前腕・手首の意味づけがまだ曖昧
- ここを本格修正するなら、左手だけ再生成/再分類する必要があるかもしれない

### 4.3 オリジナルV50より退化して見える懸念

ユーザー目視では、何度か「オリジナルV50の方が良い」と感じられている。  
現時点でも、ゲート上は改善したが、見た目比較ではまだオリジナルを明確に超えていない。

方針:

- オリジナルV50はKEEP
- 候補は比較ゲートを通るまで自動送信・昇格しない
- `REVIEW_REQUIRED` の間はTelegram送信しない

## 5. 直近の変更ファイル

主変更:

- `projects/AtsugiMechaCity/v50_final_walk_preview.py`
  - final render用肩ソケット生成
  - hidden meshをカメラboundsから除外
  - `V50_PROXY_Hand_L_*` を最終レンダーから非表示
  - default framesを180に変更
  - diagnostic locksを `--show-joint-locks` に分離

- `projects/AtsugiMechaCity/v50_joint_attachment_gate.py`
  - 肩ソケットをTORSO接触面に追加
  - `geometry_0.005` を左手首QAの可視接触面に追加

記録:

- `docs/INCIDENT_LOG.md`
  - INC-136: joint attachment gate導入
  - INC-138: diagnostic lock visible / duration mismatch
  - INC-139: shoulder socket attachment fix

- `data/state/Obsidian Vault/60_PC_Logs/Robot_Walk_INC-139_V50_shoulder_socket_attachment_20260702.md`

## 6. Fable5に相談したいこと

### 6.1 最優先で直すべき対象

関節接合ゲートはPASSしたが、連結成分が多い。  
次に直すべきはどれか。

候補:

1. 左手を再生成/再分類して、独立した `Hand_L` メッシュを作る
2. 肩・肘・手首に控えめな外装スリーブを追加して、連結成分を減らす
3. カメラ・マスク・比較ゲート側を調整し、実際に問題ある分離だけ検出する
4. 現行V50補修を続けず、PartPacker等で部品生成からやり直す

### 6.2 比較ゲートの妥当性

現在の `component_count` は、映像二値化後の大きな連結成分数で評価している。  
メカは部品が分かれて見えること自体が自然な場合もあるため、この指標が厳しすぎる可能性はあるか。

相談したい点:

- `component_count` を単純なNG指標にするべきか
- 肩/肘/手首などの関節近傍だけ局所的に見るべきか
- オリジナルV50を絶対基準にしすぎていないか
- 見た目品質と機械的接合の重み付けをどうすべきか

### 6.3 左手の扱い

`Hand_L` の安定独立メッシュが無い。  
現在は `geometry_0.005` を「rig上はforearm-end、QA上はwrist contact surface」として扱っている。

相談したい点:

- この妥協は妥当か
- 左手だけ新規生成した方がよいか
- 右手 `geometry_0.006` をミラーして左手に使うべきか
- それとも、手首から先は低優先で歩行自然さを先に詰めるべきか

### 6.4 今後の改善ループ設計

今後は以下の順で通したい。

1. original V50 baselineを保護
2. candidate生成
3. joint attachment gate
4. original compare gate
5. 目視QA
6. Telegram送信

相談したい点:

- この順序でよいか
- 追加すべきゲートはあるか
- 歩行自然さ、部品接合、見た目のどれを最適化目標にするべきか
- GPU RLへ進む前に、現行メッシュ補修をどこまで終えるべきか

## 7. Codex側の現時点推奨

現時点では、PartPackerから全面作り直しよりも、オリジナルV50を保持したまま以下を進めるのが安全。

1. component_count soft flagの原因フレーム/原因部品を特定
2. 左手・前腕・肩まわりの見た目分離を局所補修
3. original compare gateを `PASS_ORIGINAL_COMPARE` に近づける
4. その後にTelegram送信候補へ昇格

理由:

- 関節接合ゲートはすでにPASSまで来た
- 全面再生成は、また肩・手首・脚形状崩れを再発させるリスクが高い
- オリジナルV50の良さを壊さず、差分で改善する方が比較しやすい

## 8. Fable5への短い質問文

以下をそのままFable5に投げてもよい。

> V50ロボット歩行モデルについて相談です。肩・肘・手首・股・膝・足首のjoint attachment gateはPASSしましたが、オリジナルV50との映像比較では `candidate_has_more_large_disconnected_components_than_original` により `REVIEW_REQUIRED` です。左手には安定した独立メッシュがなく、`geometry_0.005` を左手首の可視接触面としてQA上だけ扱っています。次に、左手再生成・肩/肘/手首外装スリーブ追加・比較ゲート改善・PartPackerから作り直しのどれを優先すべきでしょうか。オリジナルV50は保護したまま、見た目と関節接合の両方を改善したいです。
