# 運用マニュアル

## 目的
VNCCS Pose Studioで設定したポーズ・光源・カメラ条件を、再現可能な実験条件として保存し、画像生成・品質評価・外観検査AIの学習データ作成に利用します。

## 推奨フロー
1. DOE条件表を作成
2. 各条件に対してVNCCSでポーズ・ライト・カメラを設定
3. ComfyUIで画像生成
4. 画像と条件JSONを同じIDで保存
5. Node-REDでメタデータCSVへ追記
6. 必要に応じてQdrantへベクトル登録
7. Anomalib等で学習/評価

## 命名規則
- 生成画像：`VNCCS_YYYYMMDD_HHMMSS_conditionID.png`
- 条件JSON：`VNCCS_YYYYMMDD_HHMMSS_conditionID.json`
- 評価CSV：`vnccs_generation_log.csv`

## 評価項目例
- pose_match_score：指定ポーズに近いか
- lighting_match_score：光源条件が反映されているか
- identity_consistency：同一キャラとして維持されているか
- defect_visibility：外観検査用途で欠陥が見えやすいか
- usability_flag：採用/保留/破棄

## 現場利用の注意
外観検査AIに使用する場合、生成画像だけで判断せず、必ず実写データとの混合・比較・検証を行ってください。
