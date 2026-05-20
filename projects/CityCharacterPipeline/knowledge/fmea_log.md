
## FMEA — hon_atsugi_dom (2026-05-17 02:57)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — hon_atsugi_dom (2026-05-17 02:58)

QAスコア: material=2 lighting=2 camera=3 character=2

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 4 | 3 | **96** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 3 | 4 | **84** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
ambientCGアセットをpipeline実行前にダウンロードし、パスを確認すること / Nishita Sky + sun_energy>=5 + fill_lights 2灯を必ず設定すること / embed_depth=0.75固定 + ShadowCatcher必須。Mixamoポーズfbxを使用すること


## FMEA — hon_atsugi_dom (2026-05-17 02:59)

QAスコア: material=1 lighting=1 camera=2 character=1

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 4 | 3 | **96** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 3 | 4 | **84** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
ambientCGアセットをpipeline実行前にダウンロードし、パスを確認すること / Nishita Sky + sun_energy>=5 + fill_lights 2灯を必ず設定すること / カメラtargetをキャラクター重心（height_m/2）に合わせること / embed_depth=0.75固定 + ShadowCatcher必須。Mixamoポーズfbxを使用すること


## FMEA — hon_atsugi_dom (2026-05-17 03:01)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — hon_atsugi_dom (2026-05-17 03:04)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — hon_atsugi_dom (2026-05-17 03:45)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — hon_atsugi_dom (2026-05-17 03:50)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — hon_atsugi_dom (2026-05-17 03:59)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-17 08:21)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-17 08:22)

QAスコア: material=4 lighting=4 camera=4 character=4

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-17 08:27)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-17 08:32)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-17 08:42)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 09:12)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
Blenderエラー: timeout


## FMEA — Shibuya_Zaku (2026-05-18 09:40)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 10:19)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 10:27)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 10:46)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 11:08)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 11:21)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 11:25)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 11:29)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 11:33)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 11:37)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 11:40)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 11:43)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 11:53)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 12:02)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 12:29)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 12:35)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 12:38)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 12:41)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 12:49)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 12:55)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 12:59)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 13:38)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 13:43)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 13:48)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 14:22)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 15:24)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 15:24)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 15:41)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA -- infra_cp932_fix_20260518 (2026-05-18 16:35)

カテゴリ: DBセルフヒーラー / インフラ

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| replay_pending_queue | print文でUnicodeEncodeError | DB接続成功をDB失敗と誤認しリプレイ不能 | cp932 stdoutがU+2014をエンコード不能 | 9 | 7 | 8 | **504** | stdout.reconfigure(utf-8) + print文の--をASCIIに置換 |
| knowledge_recorder | 同上 | DBリトライログが cp932 で落ちる | 同上 | 9 | 7 | 8 | **504** | 同上 |

### 教訓
日本語Windows環境では stdout encoding=cp932 のためUnicode特殊文字(-- U+2014, -- U+2192等)がprint文でクラッシュする。
全Pythonモジュールの先頭に sys.stdout.reconfigure(encoding=utf-8, errors=replace) を追加し、print文はASCII安全な文字のみ使用すること。


## FMEA — Shibuya_Zaku (2026-05-18 17:28)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 17:29)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 17:35)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 19:21)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 19:31)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 19:42)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 19:51)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 20:00)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 20:08)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 20:17)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 20:25)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 20:33)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 20:41)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 20:54)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 21:02)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 22:02)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 22:05)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 22:20)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 23:01)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 23:17)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 23:29)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 23:41)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-18 23:51)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 06:29)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 06:49)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 07:03)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 07:14)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 07:25)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 07:37)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 07:49)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 07:57)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 10:27)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 10:28)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 10:34)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 10:41)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 10:48)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 11:25)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 11:35)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 11:54)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 12:08)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 12:15)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 12:19)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 15:34)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 20:17)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 20:27)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 20:33)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 20:47)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 20:50)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 21:34)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 21:46)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 21:51)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 22:02)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 22:07)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 22:19)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 22:48)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 22:56)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-19 23:00)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 05:16)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 05:34)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 05:38)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 05:42)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 05:58)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 06:05)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 06:14)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 06:48)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 06:48)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 06:50)

QAスコア: material=4 lighting=4 camera=4 character=4

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 06:53)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 06:54)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 06:59)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 08:26)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 08:46)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 08:56)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 09:11)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 09:44)

QAスコア: material=5 lighting=5 camera=5 character=5

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。


## FMEA — Shibuya_Zaku (2026-05-20 09:53)

QAスコア: material=3 lighting=3 camera=3 character=3

| 工程 | 故障モード | 影響 | 原因 | 重篤度 | 発生度 | 検出度 | RPN | 対策 |
|---|---|---|---|---|---|---|---|---|
| マテリアル | 白箱（PBR未適用） | リアリズム低下 | ambientCGアセット不在 | 8 | 2 | 3 | **48** | アセット事前ダウンロード確認 / fallback Principled |
| ライティング | フラット照明 | 深度感なし | HDRI/太陽未設定 | 7 | 1 | 4 | **28** | Nishita Sky + sun_energy≥5 + fill2灯 |
| 接地AO | DOM浮き | 不自然な接地 | Raycast miss / embed_depth不足 | 9 | 3 | 3 | **81** | embed_depth=0.75固定 + ShadowCatcher必須 |
| カメラ | T-ポーズシルエット | キャラ品質低下 | Mixamo未適用 | 8 | 2 | 3 | **48** | posed FBX使用 / シルエット事前チェック |
| レンダリング | 全黒フレーム | 成果物なし | Emission未接続 | 10 | 2 | 2 | **40** | visual_qa gate / samples≥64 |
| アニメーション | フレーム間照明変化 | 動画品質低下 | ライト設定非固定 | 6 | 3 | 4 | **72** | 全フレームで同一照明パラメータ固定 |

### 教訓
全項目合格。このパラメータ設定を再利用推奨。

## FMEA - RickDias Walking Movie Baseline (2026-05-20)

Reference playbook: `docs/knowledge/city_character_pipeline_video_generation_playbook_20260520.md`
Beads: `iatf_system-ckb`
Incident: `INC-085`

| Failure mode | Effect | Cause | S | O | D | RPN | Control |
|---|---|---|---:|---:|---:|---:|---|
| FBX texture overwritten | robot appears untextured | fallback PBR replaces imported image nodes | 8 | 4 | 4 | 128 | preserve existing texture materials |
| Stale frames encoded | wrong duration or old motion appears | old PNG frames remain after shorter render | 7 | 5 | 3 | 105 | clean frame prefix before render |
| Motion looks static | walking reads as stopped | frame count increased and stride/playback slowed too much | 7 | 4 | 5 | 140 | keep 90f/5.0m/scale 1.0 baseline |
| Lower body looks buried | presentation fails | OSM foreground/camera corridor occlusion | 9 | 4 | 4 | 144 | hide walk and camera corridor occluders |
| Feet actually below terrain | physical grounding error | per-frame lift missing | 9 | 3 | 3 | 81 | use per-frame clearance logs |
| Character leaves camera | black or poor framing | imported object/root transform curves | 8 | 3 | 4 | 96 | remove object transform curves |
| Blender action cleanup fails | render aborts | Blender 5.x Layered Action API mismatch | 8 | 3 | 3 | 72 | support `channelbags` plus old `fcurves` |
| Local LLM over-refactors | new regressions | small model changes too much code at once | 8 | 4 | 6 | 192 | config-first, one hypothesis per run |
