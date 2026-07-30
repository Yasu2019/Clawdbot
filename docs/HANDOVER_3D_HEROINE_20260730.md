# 3Dキャラクター再生成 引継ぎ

- 日時: 2026-07-30 JST
- Beads: `Clawdbot_Docker_20260125-hc0l`
- 承認範囲: 本生成タスク内の修正・再試行を最大50回まで承認済み
- 実施済み: 再試行11回

## 現在の採用成果

クリーンなスタイライズド人物モデルとして、形状破綻のない34パーツ、
19ボーン、72フレームのモーションを生成した。

| 成果物 | フルパス |
|---|---|
| Blender | `D:\Clawdbot_Docker_20260125\vnccs_comfyui_clawstack_pro\ComfyUI_app\output\3d\quality_rebuild_20260730\clean_rigged_v3\clean_heroine_v3_rigged.blend` |
| Unity向けFBX | `D:\Clawdbot_Docker_20260125\vnccs_comfyui_clawstack_pro\ComfyUI_app\output\3d\quality_rebuild_20260730\clean_rigged_v3\clean_heroine_v3_rigged.fbx` |
| GLB | `D:\Clawdbot_Docker_20260125\vnccs_comfyui_clawstack_pro\ComfyUI_app\output\3d\quality_rebuild_20260730\clean_rigged_v3\clean_heroine_v3_rigged.glb` |
| 動画 | `D:\Clawdbot_Docker_20260125\vnccs_comfyui_clawstack_pro\ComfyUI_app\output\3d\quality_rebuild_20260730\clean_rigged_v3\clean_heroine_v3_motion.mp4` |
| 基準画像 | `D:\Clawdbot_Docker_20260125\vnccs_comfyui_clawstack_pro\ComfyUI_app\output\3d\quality_rebuild_20260730\clean_rigged_v3\clean_heroine_v3_frame_001.png` |
| 生成レポート | `D:\Clawdbot_Docker_20260125\vnccs_comfyui_clawstack_pro\ComfyUI_app\output\3d\quality_rebuild_20260730\clean_rigged_v3\clean_heroine_v3_report.json` |
| 再生成スクリプト | `D:\Clawdbot_Docker_20260125\vnccs_comfyui_clawstack_pro\scripts\build_clean_rigged_heroine_v3.py` |

## 検証結果

- FBX/GLB/Blend: 書き出し成功
- 動画: H.264、720x900、24 fps、72フレーム、3.0秒
- 目視対象: 1、18、36、54、72フレーム
- 合格: パーツ分離、四肢追従、スカート固定、貫通・扇状伸長なし
- 品質区分: クリーンなスタイライズド3D
- 未達: 写実またはハイエンド有機スカルプ相当ではない
- Unityインポート: 未実施。既存Unity資産保護のため、本セッションではFBX生成まで。

## 不採用結果と判断

Hunyuan3D v2.1の4096潜在解像度出力は、正面形状は改善したが、衣装・
スカート・脚が単一メッシュ内で融合し、重複面も検出された。正面画像投影と
決定論的ウェイトを試したが、ポーズ時にスカートが扇状に伸びたため不採用。
元出力は証拠として削除せず保存している。

## GPU・タスク状態

- 本タスク用ComfyUI (`127.0.0.1:8291`): 生成後に停止済み
- GPU確認値: 8%、VRAM 70 MiB、47℃（停止直後。デスクトップ負荷を含む）
- 次の既存スケジュールタスクはDisabledのまま:
  - `Clawstack_Motion_Learning_Supervisor`
  - `Clawstack_Robot_L20_Autonomous_Loop`
  - `Clawstack_Robot_L20_Watchdog`
- 上記は別承認なしに再有効化しない。

## 次の安全な作業

1. 新規バージョンフォルダーへFBXを複製し、Unity 6000.0.73f1でインポートする。
2. 既存Prefab、Controller、manifest、Build Settingsは変更しない。
3. Unity上で72フレームの動作とマテリアルを確認する。
4. 人物の造形品質をさらに上げる場合は、正面1枚ではなく正面・側面・背面の
   3面図を入力にし、衣装別メッシュ生成または手動リトポロジーを行う。
