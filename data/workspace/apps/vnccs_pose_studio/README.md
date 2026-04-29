# VNCCS Pose Studio × ComfyUI × Clawstack 完全自動データ生成ライン（本気版）

目的：ComfyUI上のVNCCS Pose Studioを、OpenClaw/Portal/Node-RED/DOE管理と連携し、ポーズ・光源・構図を再現可能な条件として管理するための追加パッケージです。

## 重要方針
- 既存Clawstackを直接上書きしません。
- Portalには追加カードとして配置します。
- ComfyUIワークフローJSONは雛形です。実際のVNCCS公式/配布ワークフローJSONを `comfyui/workflows/official/` に置いてから使用してください。
- 生成画像、条件JSON、評価CSVをセットで保存し、後からDOE・外観検査AI・教材化に使える構成にしています。

## 推奨配置
Windows側例：
`C:\clawstack\extensions\vnccs_pose_studio_pro\`

WSL/Docker側例：
`/opt/clawstack/extensions/vnccs_pose_studio_pro/`

## 初回手順
1. このZIPを展開
2. `docs/INSTALL_GUIDE_JA.md` を読む
3. VNCCS Pose Studioの公式/配布元からComfyUIワークフローJSONを入手
4. ComfyUI ManagerでMissing Custom Nodesを導入
5. モデル類をComfyUIの所定フォルダへ配置
6. `portal/apps/vnccs_pose_studio/` をPortal静的配信先へコピー
7. Node-REDへ `flows/node_red/vnccs_dataset_flow.json` を読み込み
8. `scripts/generate_doe_plan.py` でDOE条件表を作成

## 成果物
- ComfyUI連携用条件管理テンプレ
- Node-REDフロー雛形
- PortalカードHTML
- DOE生成スクリプト
- OpenClaw用プロンプト/ツール仕様
- 導入・運用・事故防止手順書

