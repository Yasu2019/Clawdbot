import bpy
import os

filepath = r'D:\Clawdbot_Docker_20260125\data\workspace\bulma_remotion\public\bulma_mc.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=filepath)

# アーマチュアを探して骨の名前をリストアップ
armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
if armatures:
    arm = armatures[0]
    print('--- BONES FOUND ---')
    for bone in arm.data.bones:
        print(f'Bone: {bone.name}')
else:
    print('No armature found in the GLB')
