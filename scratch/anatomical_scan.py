import bpy
import numpy as np

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

verts = np.array([(obj.matrix_world @ v.co) for v in obj.data.vertices])
z_min, z_max = verts[:, 2].min(), verts[:, 2].max()

# 0.05m 刻みで横幅をスキャン
print('Z-Level Scan (Width):')
for z_target in np.linspace(z_min, z_max, 30):
    # その高さ付近の頂点を抽出
    mask = (verts[:, 2] > z_target - 0.05) & (verts[:, 2] < z_target + 0.05)
    level_verts = verts[mask]
    if len(level_verts) > 0:
        # X軸の広がり（幅）を計算
        width = level_verts[:, 0].max() - level_verts[:, 0].min()
        print(f'Z={z_target:.2f}, Width={width:.2f}')
