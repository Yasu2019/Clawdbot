import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = bpy.context.selected_objects[0]

# メッシュの境界を再確認
min_b = obj.bound_box[0]
max_b = obj.bound_box[6]
z_min, z_max = min_b[2], max_b[2]
y_center = (min_b[1] + max_b[1]) / 2
x_center = (min_b[0] + max_b[0]) / 2

# アーマチュア作成 (Z軸が高さ)
bpy.ops.object.armature_add(location=(x_center, y_center, z_min))
arm = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones

# Spine
spine = eb[0]
spine.name = 'Spine'
spine.head = (x_center, y_center, z_min + 0.3)
spine.tail = (x_center, y_center, z_min + 0.8)

# Neck
neck = eb.new('Neck')
neck.head = (x_center, y_center, z_min + 0.8)
neck.tail = (x_center, y_center, z_min + 1.1)
neck.parent = spine

# Head
head = eb.new('Head')
head.head = (x_center, y_center, z_min + 1.1)
head.tail = (x_center, y_center, z_min + 1.3)
head.parent = neck

bpy.ops.object.mode_set(mode='OBJECT')

# スキニング
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
