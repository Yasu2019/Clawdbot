import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

# 骨の配置
x_c, y_c, z_min = 0.005, -0.03, -0.74
bpy.ops.object.armature_add(location=(x_c, y_c, z_min))
arm = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
# 身長に合わせて骨の長さを調整
s = eb[0]; s.name = 'Spine'; s.head = (0,0, 0.4); s.tail = (0,0, 0.7)
n = eb.new('Neck'); n.head = (0,0, 0.7); n.tail = (0,0, 1.0); n.parent = s
h = eb.new('Head'); h.head = (0,0, 1.0); h.tail = (0,0, 1.3); h.parent = n
bpy.ops.object.mode_set(mode='OBJECT')

obj.parent = arm
mod = obj.modifiers.new(name="Armature", type='ARMATURE')
mod.object = arm

# 頂点グループの再作成
for vg in obj.vertex_groups: obj.vertex_groups.remove(vg)
vg_spine = obj.vertex_groups.new(name="Spine")
vg_neck = obj.vertex_groups.new(name="Neck")
vg_head = obj.vertex_groups.new(name="Head")

# 【重要】最適化した境界線でウェイトを割り当て
for v in obj.data.vertices:
    z = (obj.matrix_world @ v.co).z
    if z > 0.35: # 顔全体をカバー
        vg_head.add([v.index], 1.0, 'REPLACE')
    elif z > 0.05: # 首・肩をカバー
        vg_neck.add([v.index], 1.0, 'REPLACE')
    else: # 胴体をカバー
        vg_spine.add([v.index], 1.0, 'REPLACE')

bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
print('Joint boundaries optimized and rigging completed')
