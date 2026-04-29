import bpy
import os
import numpy as np

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

# スキャン結果に基づいた座標
x_c, y_c = 0.005, -0.03
# 支点を Z=0.32 (首の付け根) に設定
bpy.ops.object.armature_add(location=(x_c, y_c, 0.32))
arm = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
s = eb[0]; s.name = 'Spine'; s.head = (0,0,-0.5); s.tail = (0,0, 0.0) # 胸
n = eb.new('Neck'); n.head = (0,0, 0.0); n.tail = (0,0, 0.1); n.parent = s # 首
h = eb.new('Head'); h.head = (0,0, 0.1); h.tail = (0,0, 0.3); h.parent = n # 頭
bpy.ops.object.mode_set(mode='OBJECT')

obj.parent = arm
mod = obj.modifiers.new(name="Armature", type='ARMATURE')
mod.object = arm

# 頂点グループ作成
for vg in obj.vertex_groups: obj.vertex_groups.remove(vg)
vg_spine = obj.vertex_groups.new(name="Spine")
vg_neck = obj.vertex_groups.new(name="Neck")
vg_head = obj.vertex_groups.new(name="Head")

# スムーズなウェイト割り当て
for v in obj.data.vertices:
    z = (obj.matrix_world @ v.co).z
    if z > 0.45:
        vg_head.add([v.index], 1.0, 'REPLACE')
    elif z > 0.32:
        # 首から頭へのグラデーション
        w = (z - 0.32) / (0.45 - 0.32)
        vg_head.add([v.index], w, 'REPLACE')
        vg_neck.add([v.index], 1.0 - w, 'REPLACE')
    elif z > 0.25:
        # 体から首へのグラデーション
        w = (z - 0.25) / (0.32 - 0.25)
        vg_neck.add([v.index], w, 'REPLACE')
        vg_spine.add([v.index], 1.0 - w, 'REPLACE')
    else:
        vg_spine.add([v.index], 1.0, 'REPLACE')

bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
print('Anatomical rigging with smooth weights completed')
