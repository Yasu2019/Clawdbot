import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'
check_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\rig_check_side.png'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
obj = bpy.context.selected_objects[0]

# 計測された中心値を使用
x_c = 0.005
y_c = -0.03
z_min = -0.74

# アーマチュア作成
bpy.ops.object.armature_add(location=(x_c, y_c, z_min))
arm = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones

# 骨の長さをキャラクターの身長（1.4m）に合わせて調整
s = eb[0]; s.name = 'Spine'; s.head = (x_c, y_c, -0.3); s.tail = (x_c, y_c, 0.2)
n = eb.new('Neck'); n.head = (x_c, y_c, 0.2); n.tail = (x_c, y_c, 0.4); n.parent = s
h = eb.new('Head'); h.head = (x_c, y_c, 0.4); h.tail = (x_c, y_c, 0.6); h.parent = n

bpy.ops.object.mode_set(mode='OBJECT')

# 強制的にウェイトを付与
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# --- デバッグ画像生成（真横から） ---
bpy.ops.object.camera_add(location=(3, y_c, 0), rotation=(1.57, 0, 1.57))
bpy.context.scene.camera = bpy.context.object
# 骨を目印（球）で可視化
for bone in arm.data.bones:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=bone.head_local)
    mat = bpy.data.materials.new(name="Red")
    mat.diffuse_color = (1, 0, 0, 1)
    bpy.context.active_object.data.materials.append(mat)

bpy.context.scene.render.filepath = check_path
bpy.ops.render.render(write_still=True)
# --------------------------------

bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
