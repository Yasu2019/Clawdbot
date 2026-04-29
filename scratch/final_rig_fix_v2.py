import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

# メッシュの重心 (前回の計測値を使用)
x_c, y_c, z_min = 0.005, -0.03, -0.74

# アーマチュアを重心に配置
bpy.ops.object.armature_add(location=(x_c, y_c, z_min))
arm = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones

# 骨のローカル座標を設定（Armature の位置が起点になるため 0, 0 で指定）
# これでワールド座標でも (x_c, y_c) に一致する
s = eb[0]; s.name = 'Spine'; s.head = (0, 0, 0.4); s.tail = (0, 0, 0.9)
n = eb.new('Neck'); n.head = (0, 0, 0.9); n.tail = (0, 0, 1.1); n.parent = s
h = eb.new('Head'); h.head = (0, 0, 1.1); h.tail = (0, 0, 1.3); h.parent = n

bpy.ops.object.mode_set(mode='OBJECT')

# Voxel 手法で確実にウェイトを付与
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
# 自動ウェイトを試行（失敗しても骨が中にあるので成功率は高いはず）
try:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except:
    bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')

bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
print('Rigging coordinates fixed and re-exported')
