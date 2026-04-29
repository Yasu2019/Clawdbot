import bpy
import numpy as np

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

verts = np.array([(obj.matrix_world @ v.co) for v in obj.data.vertices])

print('--- Anatomical Landmarks Scan ---')

# 1. 首の高さ (前回特定済み)
neck_z = 0.36

# 2. 肩の特定 (首の少し下で X 軸の広がりが最大になる場所)
shoulder_search_z = neck_z - 0.1
mask = (verts[:, 2] > shoulder_search_z - 0.05) & (verts[:, 2] < shoulder_search_z + 0.05)
s_verts = verts[mask]
if len(s_verts) > 0:
    left_shoulder_x = s_verts[:, 0].min()
    right_shoulder_x = s_verts[:, 0].max()
    print(f'Shoulder Height: Z={shoulder_search_z:.2f}')
    print(f'Left Shoulder: X={left_shoulder_x:.2f}, Y={s_verts[:, 1].mean():.2f}')
    print(f'Right Shoulder: X={right_shoulder_x:.2f}, Y={s_verts[:, 1].mean():.2f}')

# 3. 肘・手の特定 (腕の広がりを追跡)
for z in np.linspace(shoulder_search_z - 0.1, -0.5, 10):
    mask = (verts[:, 2] > z - 0.05) & (verts[:, 2] < z + 0.05)
    v_level = verts[mask]
    if len(v_level) > 0:
        l_x = v_level[:, 0].min()
        r_x = v_level[:, 0].max()
        print(f'Z={z:.2f} -> Arm Spread X: [{l_x:.2f} to {r_x:.2f}]')

# 4. 腰の特定 (胴体の中心付近で幅が一定になる場所)
waist_z = -0.1
print(f'Waist Height: Z={waist_z:.2f}')
