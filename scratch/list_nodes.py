import trimesh

glb_path = r'D:\Clawdbot_Docker_20260125\data\workspace\bulma_remotion\public\bulma_mc.glb'
scene = trimesh.load(glb_path, process=False)

print('Nodes in GLB:')
for name in scene.graph.nodes:
    print(f'- {name}')
