import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'
render_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\rig_check.png'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)

# カメラの設定
bpy.ops.object.camera_add(location=(0, 0, 5), rotation=(0, 0, 0))
bpy.context.scene.camera = bpy.context.object

# 表示設定：骨をメッシュの前に表示（X-Ray モードのような設定）
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        obj.show_in_front = True
        obj.display_type = 'WIRE'
    if obj.type == 'MESH':
        obj.display_type = 'TEXTURED'

# 背景をグレーにして見やすくする
bpy.context.scene.render.resolution_x = 800
bpy.context.scene.render.resolution_y = 800
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.filepath = render_path

# ビューポートの表示をレンダリング（OpenGL レンダリング）
bpy.ops.render.opengl(write_still=True)
print(f'Rig check image saved to {render_path}')
