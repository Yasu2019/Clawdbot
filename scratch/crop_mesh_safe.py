import trimesh
import numpy as np

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_color_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'

scene = trimesh.load(src_path, process=False)
new_scene = trimesh.Scene()

for name, geometry in scene.geometry.items():
    if isinstance(geometry, trimesh.Trimesh):
        # スライス
        cropped = geometry.slice_plane(plane_origin=[-0.23, 0, 0], plane_normal=[1, 0, 0])
        cropped = cropped.slice_plane(plane_origin=[0.24, 0, 0], plane_normal=[-1, 0, 0])
        
        # 頂点が残っている場合のみ追加
        if len(cropped.vertices) > 0:
            new_scene.add_geometry(cropped, node_name=name)

new_scene.export(dest_path)
print('Successfully exported with corrected script')
