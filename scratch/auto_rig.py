import bpy
import os

# パス設定
src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

# シーンをクリア
bpy.ops.wm.read_factory_settings(use_empty=True)

# GLB をインポート
bpy.ops.import_scene.gltf(filepath=src_path)
obj = bpy.context.selected_objects[0]

# 簡易的な骨を作成（中心線に配置）
bpy.ops.object.armature_add(location=(0, 0, 0))
arm = bpy.context.active_object
arm.name = 'Bulma_Armature'

# メッシュと骨を選択してペアレント（自動ウェイト）
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# GLB としてエクスポート
bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
print('Auto-rigging completed')
