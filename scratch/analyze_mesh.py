import trimesh
import numpy as np

glb_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_Segmentation_mc.glb'
scene = trimesh.load(glb_path)

# 全メッシュを統合して範囲を確認
if isinstance(scene, trimesh.Scene):
    mesh = scene.dump(concatenate=True)
else:
    mesh = scene

bounds = mesh.bounds
print(f'Bounds Min: {bounds[0]}')
print(f'Bounds Max: {bounds[1]}')

# X軸（横方向）の範囲を 3 分割して、中央か左側を抜き出す準備
x_min, y_min, z_min = bounds[0]
x_max, y_max, z_max = bounds[1]
width = x_max - x_min

# 正面が左側にあると仮定して切り取ってみる（後で調整可能）
# ここでは一旦、情報を出力するだけ
