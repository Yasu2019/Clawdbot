from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import os

app = FastAPI()

# ブラウザからのアクセスを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BLENDER_PATH = r'C:\Program Files\Blender Foundation\Blender 5.0\blender.exe'
SCRATCH_DIR = r'D:\Clawdbot_Docker_20260125\scratch'
ASSET_DIR = r'D:\Clawdbot_Docker_20260125\data\meshy_assets'

class RigRequest(BaseModel):
    model_name: str
    spine_z: float
    neck_z: float
    head_z: float

def run_blender_rig(req: RigRequest):
    script_path = os.path.join(SCRATCH_DIR, 'gui_auto_rig.py')
    src_path = os.path.join(ASSET_DIR, req.model_name)
    dest_path = os.path.join(ASSET_DIR, 'bulma_rigged.glb')
    
    script = f'''
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"{src_path}")
obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

x_c, y_c = 0.005, -0.03
z_min = -0.74

bpy.ops.object.armature_add(location=(x_c, y_c, z_min))
arm = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
s = eb[0]; s.name = 'Spine'; s.head = (0,0, 0.4); s.tail = (0,0, {req.neck_z} + 0.74)
n = eb.new('Neck'); n.head = (0,0, {req.neck_z} + 0.74); n.tail = (0,0, {req.head_z} + 0.74); n.parent = s
h = eb.new('Head'); h.head = (0,0, {req.head_z} + 0.74); h.tail = (0,0, {req.head_z} + 1.0); h.parent = n
bpy.ops.object.mode_set(mode='OBJECT')

obj.parent = arm
mod = obj.modifiers.new(name="Armature", type='ARMATURE')
mod.object = arm
for vg in obj.vertex_groups: obj.vertex_groups.remove(vg)
vg_spine = obj.vertex_groups.new(name="Spine")
vg_neck = obj.vertex_groups.new(name="Neck")
vg_head = obj.vertex_groups.new(name="Head")

for v in obj.data.vertices:
    z = (obj.matrix_world @ v.co).z
    if z > {req.head_z}:
        vg_head.add([v.index], 1.0, 'REPLACE')
    elif z > {req.neck_z}:
        w = (z - {req.neck_z}) / ({req.head_z} - {req.neck_z})
        vg_head.add([v.index], w, 'REPLACE')
        vg_neck.add([v.index], 1.0 - w, 'REPLACE')
    elif z > {req.spine_z}:
        w = (z - {req.spine_z}) / ({req.neck_z} - {req.spine_z})
        vg_neck.add([v.index], w, 'REPLACE')
        vg_spine.add([v.index], 1.0 - w, 'REPLACE')
    else:
        vg_spine.add([v.index], 1.0, 'REPLACE')

bpy.ops.export_scene.gltf(filepath=r"{dest_path}", export_format='GLB', export_skins=True)
'''
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)
    
    subprocess.run([BLENDER_PATH, '--background', '--python', script_path])

@app.post("/rig")
async def rig_model(req: RigRequest, bg_tasks: BackgroundTasks):
    bg_tasks.add_task(run_blender_rig, req)
    return {"status": "started", "message": "Rigging in progress..."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18985)
