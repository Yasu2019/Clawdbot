# 仮想材料による穴付き箱モデルのE2E通し試験

## 目的

実測材料データを取得した後に「入力は受け付けたが計算できない」状態を避けるため、仮想PP材料カードで材料入力からOpenFOAM、後処理、CalculiX、動画出力までを通した。結果は実測校正前のスクリーニングであり、設計値・品質保証値ではない。

## 実行結果

- モデル: 100 x 60 x 50 mm、4ゲート、直径3 mmベント4個、SIメッシュ
- OpenFOAM: `open_top_shell_vent4_r15_case3`、最終5 s、終了コード正常、平均alpha=0.99999998
- 仮想材料カード: `virtual_PP_injection_screening_v1`、`VIRTUAL_SCREENING_ONLY`
- 後処理入力: 67,165セルのVTUに `arrival_time_s`、`temperature_C_proxy`、`pressure_MPa_calibrated`、`gate_id` を明示的に付加
- 品質スクリーニング: 反り・ヒケ・ウエルド相対リスクのVTU/PNGを生成
- 空気トラップ: 最終充填率からの候補場を生成（平均2.33e-8、最大0.00109、候補なしに相当）
- CalculiX: 仮想圧力8.5 MPa、仮想収縮1.5%で実行終了。数値健全性監査は最大変位0.1756 mm、`PASS_NUMERICAL_SANITY_UNVALIDATED`
- 動画: `artifacts/box_roundhole_v5/virtual_e2e_20260909/videos/` に反り・ヒケ・ウエルド・空気トラップを個別出力しTelegram送信済み

## 実測データへの差し替え契約

同じ材料カード検証を通し、PVT、CTE、冷却曲線、Cross-WLF粘度、圧力/流量測定を置き換える。置換後に再実行する項目は、OpenFOAMの温度・粘度・密度連成、前線到達場、CalculiXへの場写像、メッシュ収束、実測校正である。仮想値のままでは反り量、ヒケ深さ、ウエルド強度を主張しない。

