import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = bpy.context.selected_objects[0]

# アーマチュアの作成
bpy.ops.object.armature_add(location=(0, 0, 0))
arm = bpy.context.active_object
arm.name = 'Bulma_Armature'

# 編集モードで、Y軸（上下）に骨を配置
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
# Spine (腰から胸)
spine = eb[0]
spine.name = 'Spine'
spine.head = (0, -0.4, 0)
spine.tail = (0, 0.1, 0)

# Neck (首)
neck = eb.new('Neck')
neck.head = (0, 0.1, 0)
neck.tail = (0, 0.4, 0)
neck.parent = spine

# Head (頭)
head = eb.new('Head')
head.head = (0, 0.4, 0)
head.tail = (0, 0.7, 0)
head.parent = neck

bpy.ops.object.mode_set(mode='OBJECT')

# ウェイト付与
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
# 自動ウェイトが失敗しやすいので、距離ベース（Envelope）も検討
try:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except:
    bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')

# 書き出し
bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
