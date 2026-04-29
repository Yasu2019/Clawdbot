import bpy
import os

src_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_single_mc.glb'
dest_path = r'D:\Clawdbot_Docker_20260125\data\meshy_assets\bulma_rigged.glb'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src_path)
original_obj = [o for o in bpy.data.objects if o.type == 'MESH'][0]

# 1. Voxel Helper
bpy.ops.object.select_all(action='DESELECT')
original_obj.select_set(True)
bpy.context.view_layer.objects.active = original_obj
bpy.ops.object.duplicate()
voxel_obj = bpy.context.active_object

mod = voxel_obj.modifiers.new(name="Remesh", type='REMESH')
mod.mode = 'VOXEL'
mod.voxel_size = 0.02
bpy.ops.object.modifier_apply(modifier="Remesh")

# 2. 骨
x_c, y_c, z_min = 0.005, -0.03, -0.74
bpy.ops.object.armature_add(location=(x_c, y_c, z_min))
arm = bpy.context.active_object
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
s = eb[0]; s.name = 'Spine'; s.head = (x_c, y_c, -0.3); s.tail = (x_c, y_c, 0.2)
n = eb.new('Neck'); n.head = (x_c, y_c, 0.2); n.tail = (x_c, y_c, 0.4); n.parent = s
h = eb.new('Head'); h.head = (x_c, y_c, 0.4); h.tail = (x_c, y_c, 0.6); h.parent = n
bpy.ops.object.mode_set(mode='OBJECT')

# 3. ウェイト計算
bpy.ops.object.select_all(action='DESELECT')
voxel_obj.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')

# 4. ウェイト転送 (Blender 5.0 準拠)
bpy.ops.object.select_all(action='DESELECT')
original_obj.select_set(True)
bpy.context.view_layer.objects.active = original_obj
dt_mod = original_obj.modifiers.new(name="Transfer", type='DATA_TRANSFER')
dt_mod.object = voxel_obj
dt_mod.use_vert_data = True
dt_mod.data_types_verts = {'VGROUP_WEIGHTS'}
dt_mod.vert_mapping = 'NEAREST' # Blender 5.0 での変更
bpy.ops.object.datalayout_transfer(modifier="Transfer")
bpy.ops.object.modifier_apply(modifier="Transfer")

# 5. 仕上げ
arm_mod = original_obj.modifiers.new(name="Armature", type='ARMATURE')
arm_mod.object = arm
bpy.data.objects.remove(voxel_obj, do_unlink=True)
bpy.ops.export_scene.gltf(filepath=dest_path, export_format='GLB', export_skins=True)
print('Voxel rigging successfully completed for Blender 5.0')
