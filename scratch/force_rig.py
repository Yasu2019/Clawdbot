import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = bpy.context.selected_objects[0]

# メッシュの境界から骨を正確に配置（Z軸高さ）
min_b = obj.bound_box[0]
max_b = obj.bound_box[6]
z_min, z_max = min_b[2], max_b[2]

# アーマチュア作成
bpy.ops.object.armature_add(location=(0, 0, z_min))
arm = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones

# Spine, Neck, Head の鎖
s = eb[0]; s.name = 'Spine'; s.head = (0,0, z_min + 0.2); s.tail = (0,0, z_min + 0.7)
n = eb.new('Neck'); n.head = (0,0, z_min + 0.7); n.tail = (0,0, z_min + 1.0); n.parent = s
h = eb.new('Head'); h.head = (0,0, z_min + 1.0); h.tail = (0,0, z_min + 1.3); h.parent = n

bpy.ops.object.mode_set(mode='OBJECT')

# 【重要】強制スキニング（Envelope）
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
# 自動ウェイトをあきらめ、エンベロープ（影響範囲ベース）で結合
bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')

# 書き出し
bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
print('Envelope rigging completed')
