# 導入ガイド：VNCCS Pose Studio × ComfyUI × Clawstack

## 1. 前提
このパッケージは、VNCCS Pose Studioを直接同梱するものではありません。公式/配布元のComfyUIワークフローJSONと必要ノード・モデルを、ユーザー環境に安全に組み込むための運用テンプレートです。

## 2. ComfyUI側
### 2.1 ワークフロー
1. VNCCS Pose Studioの配布元からJSONを取得
2. ComfyUI画面へドラッグ＆ドロップ
3. Missing Custom Nodesが出た場合、ComfyUI Managerから一括インストール
4. ComfyUIを再起動

### 2.2 モデル配置例
環境により異なります。一般的には以下を確認します。

- `ComfyUI/models/checkpoints/`
- `ComfyUI/models/unet/`
- `ComfyUI/models/loras/`
- `ComfyUI/models/vae/`
- `ComfyUI/models/clip/`
- `ComfyUI/models/text_encoders/`

Flux系の場合、ワークフロー指定のモデル名と完全一致させてください。

## 3. Clawstack側
### 3.1 推奨配置
`extensions/vnccs_pose_studio_pro/` として追加配置します。

### 3.2 Portalカード追加
`portal/apps/vnccs_pose_studio/index.html` をPortalの静的アプリ配信先にコピーします。
既存Portalのカード登録方式に合わせ、`config/portal_card_snippet.json` の内容を追加してください。

### 3.3 Node-RED
`flows/node_red/vnccs_dataset_flow.json` をNode-REDにImportします。
これは以下を行う雛形です。

- 生成条件JSONの受信
- 画像保存先の監視
- メタデータCSVへの追記
- 後段のQdrant/Anomalib処理への接続点提供

## 4. 事故防止
- 既存ComfyUI/custom_nodesを一括上書きしない
- モデルファイルを同名で上書きしない
- 導入前に `checks/pre_install_checklist.md` を実行
- 大きな変更前にGitHubまたはZIPバックアップを作成

