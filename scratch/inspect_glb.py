import json
import os
from pygltflib import GLTF2

glb_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_color_mc.glb'
gltf = GLTF2.load(glb_path)

# メッシュとスキンの情報を抽出
has_skin = len(gltf.skins) > 0
has_animations = len(gltf.animations) > 0
node_count = len(gltf.nodes)

print(json.dumps({
    "has_skin": has_skin,
    "has_animations": has_animations,
    "node_count": node_count,
    "texture_count": len(gltf.images)
}, indent=2))
