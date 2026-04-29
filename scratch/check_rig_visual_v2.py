import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'
render_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\rig_check.png'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)

# 骨の情報を取得して、その場所に目印（赤い円柱）を置く
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        for bone in obj.data.bones:
            # 骨の開始地点に赤い球を置く
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=bone.head_local)
            mat = bpy.data.materials.new(name="Red")
            mat.diffuse_color = (1, 0, 0, 1)
            bpy.context.active_object.data.materials.append(mat)

# カメラとライトの設定
bpy.ops.object.camera_add(location=(0, 0, 3), rotation=(0, 0, 0))
bpy.context.scene.camera = bpy.context.object
bpy.ops.object.light_add(type='SUN', location=(0, 0, 5))

# レンダリング設定
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.filepath = render_path
bpy.ops.render.render(write_still=True)
print(f'Debug image rendered to {render_path}')
