import trimesh
import numpy as np

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_Segmentation_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'

scene = trimesh.load(src_path)
mesh = scene.to_geometry()

# スライス実行（中央 1/3 を残す）
cropped = mesh.slice_plane(plane_origin=[-0.23, 0, 0], plane_normal=[1, 0, 0])
cropped = cropped.slice_plane(plane_origin=[0.24, 0, 0], plane_normal=[-1, 0, 0])

cropped.export(dest_path)
print('Successfully exported to bulma_single_mc.glb')
