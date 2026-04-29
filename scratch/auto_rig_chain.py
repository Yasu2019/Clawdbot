import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = bpy.context.selected_objects[0]

# アーマチュアの作成
bpy.ops.object.armature_add(location=(0, -0.8, 0)) # 足元付近から開始
arm = bpy.context.active_object
arm.name = 'Bulma_Armature'

# 編集モードで骨の鎖を作る
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
root = eb[0]
root.name = 'Spine'
root.head = (0, 0, -0.5)
root.tail = (0, 0, 0.2)

# 首の骨を追加
neck = eb.new('Neck')
neck.head = (0, 0, 0.2)
neck.tail = (0, 0, 0.5)
neck.parent = root

# 頭の骨を追加
head = eb.new('Head')
head.head = (0, 0, 0.5)
head.tail = (0, 0, 0.8)
head.parent = neck

bpy.ops.object.mode_set(mode='OBJECT')

# 自動ウェイトで結合
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# 書き出し
bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
print('Chain rigging completed')
