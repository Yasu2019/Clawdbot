# INC-174 ときメモ風商用UI・リップシンク・実画面統合

## 結論

Unity 6000.0.73f1で、本編UI、会話操作、5種類の予定選択、リップシンク、
実画面レンダーを統合した。Windows Playerは終了コード0、EditModeは4/4、
実画面PNGは113,191 bytesで、顔、口、全身、UI、地面を目視確認した。

## QC工程表

| 工程 | 管理項目 | 合格基準 | 結果 |
|---|---|---|---|
| 能力測定 | BlendShape/Jaw | 実測し方式を選ぶ | 0/なし、代替方式 |
| ビルド | warning/error | 0/0 | 合格 |
| UI操作 | 会話+予定 | 2操作以上 | 2、Study |
| 口動作 | peak | 0.2超 | 0.9817447 |
| 実画面 | PNG/目視 | 10KB超、配置良好 | 113,191 bytes、合格 |
| 隔離 | 本編/試験 | runner混入なし | 合格 |

## 5Why・FTA・Fishbone

黒画像は隠し／batch表示、未達カウンタは会話適用経路の加算漏れ、構図不良は
生成した口を含むBounds、口の巨大化はFBX Headの親スケール、顔の遮蔽と白い
地面端は最終解像度でのUI配置・地面範囲不足が原因だった。依存、実行環境、
計測、形状、Transform、画面設計の六系統として分離した。

## FMEAと対策

| 故障モード | 影響 | 恒久対策 |
|---|---|---|
| 黒い証跡 | 誤合格 | 可視Player、10KB未満は失敗 |
| 操作未計上 | 機能証明不能 | 実コールバック完了時のみ加算 |
| Bounds汚染 | 構図崩れ | 元SkinnedMeshのみで算出 |
| 親スケール継承 | 口の位置・寸法崩れ | LateUpdateでワールド追従 |
| UI/地面不足 | 商品画面品質低下 | フル解像度目視ゲート |

## 制約

元モデルはBlendShape 0、Jawなしである。今回の
`ProceduralHeadMouth`は目視合格した代替表現であり、音素精密同期とは
主張しない。クラウドAPIは使用せず、決定論的な日本語会話で統合を検証した。

## 再発防止ルール

IF 顔変形ターゲットがない THEN 方式を明示した代替のみを採用し、可視Playerの
実画像でHead追従、口位置、UI遮蔽を検証する。試験runnerは本編に混入させない。

## 証跡・ロールバック

- Beads: `Clawdbot_Docker_20260125-xpi2`
- 本編: `D:\Local_AI_GameDev_Master\02_UnityProject\Assets\Scenes\TokimekiCommercialGame.unity`
- PNG: `D:\Clawdbot_Docker_20260125\logs\tokimeki_commercial_render_v6_20260727.png`
- バックアップ:
  `D:\Local_AI_GameDev_Master\_unity_project_backups\02_UnityProject_20260727_ui_lipsync`
- Manifestバックアップ: `Packages\manifest.json.bak_20260727_ui_render`
