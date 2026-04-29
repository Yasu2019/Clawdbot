import bpy
import numpy as np

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)

# シーン内の全メッシュを統合して調べる
all_verts = []
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        # ワールド座標に変換
        matrix = obj.matrix_world
        for v in obj.data.vertices:
            all_verts.append(matrix @ v.co)

if all_verts:
    verts_np = np.array(all_verts)
    v_min = verts_np.min(axis=0)
    v_max = verts_np.max(axis=0)
    v_avg = verts_np.mean(axis=0)
    print(f'WORLD_MIN: {v_min}')
    print(f'WORLD_MAX: {v_max}')
    print(f'WORLD_AVG: {v_avg}')
else:
    print('No vertices found')
