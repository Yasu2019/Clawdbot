import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)

results = []
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        groups = [g.name for g in obj.vertex_groups]
        results.append(f"Mesh '{obj.name}' has vertex groups: {groups}")
        # 実際にウェイトが割り当てられている頂点があるかチェック
        has_weight = False
        for v in obj.data.vertices:
            if len(v.groups) > 0:
                has_weight = True
                break
        results.append(f"Mesh '{obj.name}' has weighted vertices: {has_weight}")

if not results:
    results.append("No mesh objects found in GLB.")

print("\n".join(results))
