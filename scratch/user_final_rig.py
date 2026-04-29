import bpy
import os

# 単体版のパス
src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

# 座標（ユーザー様の指定値）
head_z = 0.48
neck_z = 0.26
spine_z = 0.07

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

# 骨の配置 (重心 X=0.005, Y=-0.03)
x_c, y_c = 0.005, -0.03
z_min = -0.74

bpy.ops.object.armature_add(location=(x_c, y_c, z_min))
arm = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones

# ユーザー指定値を Blender の内部座標系に変換 (+0.74m のオフセット)
s = eb[0]; s.name = 'Spine'
s.head = (0, 0, 0.4)
s.tail = (0, 0, neck_z + 0.74)

n = eb.new('Neck')
n.head = (0, 0, neck_z + 0.74)
n.tail = (0, 0, head_z + 0.74)
n.parent = s

h = eb.new('Head')
h.head = (0, 0, head_z + 0.74)
h.tail = (0, 0, head_z + 1.0)
h.parent = n

bpy.ops.object.mode_set(mode='OBJECT')

# ウェイト割り当て (スムーズ・グラデーション)
obj.parent = arm
mod = obj.modifiers.new(name="Armature", type='ARMATURE')
mod.object = arm

for vg in obj.vertex_groups: obj.vertex_groups.remove(vg)
vg_spine = obj.vertex_groups.new(name="Spine")
vg_neck = obj.vertex_groups.new(name="Neck")
vg_head = obj.vertex_groups.new(name="Head")

for v in obj.data.vertices:
    z = (obj.matrix_world @ v.co).z
    if z > head_z:
        vg_head.add([v.index], 1.0, 'REPLACE')
    elif z > neck_z:
        w = (z - neck_z) / (head_z - neck_z)
        vg_head.add([v.index], w, 'REPLACE')
        vg_neck.add([v.index], 1.0 - w, 'REPLACE')
    elif z > spine_z:
        w = (z - spine_z) / (neck_z - spine_z)
        vg_neck.add([v.index], w, 'REPLACE')
        vg_spine.add([v.index], 1.0 - w, 'REPLACE')
    else:
        vg_spine.add([v.index], 1.0, 'REPLACE')

bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
print('Rigging with USER COORDINATES (0.48, 0.26, 0.07) completed!')
