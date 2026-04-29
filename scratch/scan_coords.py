import bpy
import numpy as np

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = bpy.context.selected_objects[0]

# 頂点座標をすべて取得
verts = [v.co for v in obj.data.vertices]
verts_np = np.array(verts)

v_min = verts_np.min(axis=0)
v_max = verts_np.max(axis=0)
v_avg = verts_np.mean(axis=0)

print(f'V_MIN: {v_min}')
print(f'V_MAX: {v_max}')
print(f'V_AVG (Center of Mass): {v_avg}')
