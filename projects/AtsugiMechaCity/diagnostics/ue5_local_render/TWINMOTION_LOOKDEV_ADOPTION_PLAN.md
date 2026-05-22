# Twinmotion LookDev Adoption Plan

作成日: 2026-05-21 JST

## 結論

Twinmotion は **ADOPT_PARTIAL** とする。

目的は UE5 を置き換えることではない。  
PLATEAU/UE5 の背景を実写寄りにする前段階として、Twinmotion で「街として成立する見た目」を高速に探る。

## 現在のローカル状況

確認済み:

- UE5 は実装済み。
- PLATEAU 本厚木 city-only FBX は生成済み。
- UE5 への FBX import / SceneCapture2D / EXR 出力は成功済み。
- Twinmotion 本体は未インストール。
- Epic Games Launcher は存在する。

主要ローカル資産:

- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/plateau_export/Hon_Atsugi_Station_Plateau_CityOnly_UE5_CmScale.fbx`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/plateau_export/Hon_Atsugi_Station_Plateau_CityOnly_UE5_Centered.fbx`
- `projects/AtsugiMechaCity/diagnostics/hon_atsugi_station/Hon_Atsugi_Station_Plateau_Mecha.blend`
- `projects/AtsugiMechaCity/diagnostics/ue5_local_render/Atsugi_UE5_plateau_city_real_asset_materialized_view.png`

## なぜ Twinmotion を使うか

今回の失敗から、品質の第一条件は「3Dであること」ではなく「街に見えること」だと分かった。

Twinmotion の役割:

- 空、太陽、天候、露出を素早く調整する。
- 人、車、樹木、街灯、路面小物を短時間で足す。
- PLATEAU の箱っぽさを、都市景観として見える方向に補正する。
- UE5 本番実装前に「正解の見た目」を作る。

UE5 の役割:

- RickDias の配置、歩行、カメラ、動画レンダー。
- 最終的なメカ統合。
- Movie Render Queue / SceneCapture2D / EXR 出力。

## 採用判断

| 項目 | 判断 |
|---|---|
| 既存UE5と競合するか | 競合しない。LookDev用途に限定すれば補助ツール |
| 新規常時サービスが増えるか | 増えない |
| Docker/Portal/n8nに影響するか | 影響なし |
| コスト | Twinmotion無料条件内なら無料 |
| 期待効果 | 高い。街らしさの探索が速い |
| リスク | Twinmotion本体のインストール容量、手動操作依存 |

判定:

```text
ADOPT_PARTIAL
```

No-go:

- Twinmotion を最終レンダラーとして固定しない。
- UE5 パイプラインを置き換えない。
- 既存FBX/UE5アセットを破壊的に再生成しない。

## 最初の検証手順

### 1. Twinmotion をインストール

Epic Games Launcher から Twinmotion をインストールする。

無料条件:

- 学生、教育、趣味利用
- または年間売上 $1M 未満などの無料条件内

### 2. FBX を読み込む

最初に読む候補:

```text
projects/AtsugiMechaCity/diagnostics/ue5_local_render/plateau_export/Hon_Atsugi_Station_Plateau_CityOnly_UE5_CmScale.fbx
```

もしスケールや位置が変なら、次を試す:

```text
projects/AtsugiMechaCity/diagnostics/ue5_local_render/plateau_export/Hon_Atsugi_Station_Plateau_CityOnly_UE5_Centered.fbx
```

### 3. まず足す要素

優先順:

1. Sky / Sun / Exposure
2. Asphalt / Sidewalk / Building material
3. Street trees
4. Vehicles
5. People
6. Street lights / traffic lights
7. Storefront-like objects or signs

重要:

看板や色を増やしすぎない。  
v6 の失敗は、色板と箱の集合が街に見えなかったこと。

### 4. カメラ

最初の評価カメラ:

- 低めの街路カメラ
- 35mm から 50mm 相当
- RickDias を置く前に「街だけで成立するか」を見る

合格条件:

- RickDias なしでも街に見える
- 路面、歩道、建物、街路樹、人/車のスケールが自然
- 画像を小さく見ても「都市景観」と分かる

## UE5 へ戻す条件

Twinmotion側で以下を満たしたら UE5 本線へ戻す。

```text
1. 街単体のスクリーンショットが成立
2. 道路と歩道の読み取りができる
3. 建物が箱だけに見えない
4. 人/車/樹木などスケール基準がある
5. カメラ位置が決まっている
```

UE5へ戻す時の作業:

- 同じカメラ条件を UE5 script に反映する。
- UE5 側で路面/歩道/建物/窓/看板/樹木/車を再現する。
- RickDias を最後に入れる。
- 先に街だけを評価し、合格してからメカ合成に進む。

## ベンチマーク

比較対象:

- v6 geometry blockout
- v7 real photo plate
- Twinmotion PLATEAU lookdev
- UE5 recreated lookdev

評価軸:

| 評価軸 | 合格条件 |
---|---|
 City readability | 一目で街に見える |
 Scale cues | 人/車/街路樹/信号などが自然 |
 Material realism | 路面と建物が単色箱に見えない |
 Camera plausibility | RickDias配置前でも構図が成立 |
 Integration readiness | UE5で再現可能 |

## 次のアクション

1. ユーザー側で Twinmotion をインストール。
2. 上記 FBX を Twinmotion に読み込み。
3. 街だけのスクリーンショットを 3 パターン作る。
4. その画像を基準に、UE5 側で再現すべき要素を分解する。
5. RickDias は最後に配置する。

## 実行ログ 2026-05-21

Codex 実行済み:

- Epic Games Launcher の存在確認。
- Twinmotion 本体は未インストールであることを確認。
- `winget search Twinmotion` を確認したが、winget パッケージは見つからなかった。
- Epic Games Launcher を起動。
- Twinmotion 公式ダウンロードページを起動。
- Twinmotion import 用 handoff フォルダを作成。
- ダウンロード済み `EpicInstaller-19.2.3-unrealEngine (1).exe` の存在と署名を確認。
- 署名は有効。
- Epic Games Launcher は既にインストール済みかつ起動中であることを確認。
- Launcher URI `com.epicgames.launcher://store/ja/p/twinmotion` を起動。

Handoff folder:

```text
projects/AtsugiMechaCity/diagnostics/ue5_local_render/twinmotion_import_handoff/
```

Handoff contents:

```text
Hon_Atsugi_Station_Plateau_CityOnly_UE5_CmScale.fbx
README_TWINMOTION_IMPORT.md
```

残タスク:

- Epic Games Launcher 上で Twinmotion をインストールする。
- Twinmotion 起動後、handoff フォルダ内の FBX を import する。

注意:

Twinmotion のインストールは Epic アカウントのログイン、無料条件確認、ライセンス同意、インストール先選択が絡むため、Codex の shell 実行だけでは完了できない。

## 重要な教訓

街背景では、最初にメカを置かない。  
まず「街だけで見られる絵」を作る。  
街が成立してから RickDias を置く。

## 実行ログ 2026-05-22

Twinmotion 起動後の import 可否確認:

- Twinmotion 2026.1 の起動を確認。
- 対象 FBX の存在を確認。
- 対象 FBX パスを Windows クリップボードへコピー。
- handoff フォルダを Explorer で開いた。
- `.fbx` には Windows の既定アプリ関連付けがないことを確認。
- Twinmotion bootstrap に FBX パスを引数として渡す方法を試したが、CLI import として確定できなかった。

判定:

- Codex shell だけで Twinmotion の Geometry Import を完了する公式・安定手段は確認できない。
- Import 自体は Twinmotion GUI で手動実行するのが安全。
- Codex が支援できる範囲は、FBX の準備、パスコピー、手順書化、Import 後の見た目評価、UE5 へ戻す要素分解。

手動 import 手順:

```text
Twinmotion footer: Import (+)
-> Geometry
-> Open
-> paste this FBX path:
D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\diagnostics\ue5_local_render\twinmotion_import_handoff\Hon_Atsugi_Station_Plateau_CityOnly_UE5_CmScale.fbx
-> Import
```

Import 後の確認点:

- 街区が箱だけに見えず、道路・歩道・建物の関係が読めるか。
- スケール感を判断できる基準物を追加できるか。
- 材質、空、太陽、露出、影、被写界深度の方向性を決められるか。
- RickDias を置く前に、街だけで成立しているか。
