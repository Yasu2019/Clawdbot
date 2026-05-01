# Blender Python: 動作ブロックのタイムマーカー作成サンプル
# BlenderのText Editorで実行
import bpy

# sample cuts: (name, start_frame, end_frame)
cuts = [
    ("CUT_001_opening_gesture", 1, 72),
    ("CUT_002_point_to_object", 73, 144),
    ("CUT_003_nod_and_pause", 145, 210),
]

scene = bpy.context.scene
scene.timeline_markers.clear()
for name, start, end in cuts:
    scene.timeline_markers.new(name + "_START", frame=start)
    scene.timeline_markers.new(name + "_END", frame=end)

scene.frame_start = cuts[0][1]
scene.frame_end = cuts[-1][2]
print("Motion markers created.")
