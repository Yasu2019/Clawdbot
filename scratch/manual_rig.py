import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

# 骨の配置 (中心座標: x_c=0.005, y_c=-0.03)
x_c, y_c, z_min = 0.005, -0.03, -0.74
bpy.ops.object.armature_add(location=(x_c, y_c, z_min))
arm = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
s = eb[0]; s.name = 'Spine'; s.head = (0, 0, 0.4); s.tail = (0, 0, 0.9)
n = eb.new('Neck'); n.head = (0, 0, 0.9); n.tail = (0, 0, 1.1); n.parent = s
h = eb.new('Head'); h.head = (0, 0, 1.1); h.tail = (0, 0, 1.3); h.parent = n
bpy.ops.object.mode_set(mode='OBJECT')

# 親子付け（ウェイトなしで開始）
obj.parent = arm
mod = obj.modifiers.new(name="Armature", type='ARMATURE')
mod.object = arm

# --- 強制的（マニュアル）なウェイト割り当て ---
# 頂点グループを作成
vg_spine = obj.vertex_groups.new(name="Spine")
vg_neck = obj.vertex_groups.new(name="Neck")
vg_head = obj.vertex_groups.new(name="Head")

# 頂点ごとに高さを見てグループに追加
for v in obj.data.vertices:
    # 頂点のワールド座標を取得 (Z軸が高さ)
    z_world = (obj.matrix_world @ v.co).z
    
    if z_world > 0.4: # 頭
        vg_head.add([v.index], 1.0, 'REPLACE')
    elif z_world > 0.1: # 首
        vg_neck.add([v.index], 1.0, 'REPLACE')
    else: # 体
        vg_spine.add([v.index], 1.0, 'REPLACE')

bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
print('Manual vertex-weight assignment completed successfully')
