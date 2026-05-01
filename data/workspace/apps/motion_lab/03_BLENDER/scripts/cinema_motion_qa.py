"""
Blender Python: cinema_motion_qa.py
読み取り中心の品質検査スクリプトです。既存データを書き換えません。
"""

import bpy

def find_armatures():
    return [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']

def scene_info():
    sc = bpy.context.scene
    return {
        "frame_start": sc.frame_start,
        "frame_end": sc.frame_end,
        "fps": sc.render.fps,
        "armature_count": len(find_armatures()),
    }

def detect_large_bone_jumps(arm, threshold=0.30, sample_step=1):
    sc = bpy.context.scene
    result = []
    prev = {}
    for f in range(sc.frame_start, sc.frame_end + 1, sample_step):
        sc.frame_set(f)
        for pb in arm.pose.bones:
            pos = arm.matrix_world @ pb.head
            if pb.name in prev:
                dist = (pos - prev[pb.name]).length
                if dist > threshold:
                    result.append((f, pb.name, round(dist, 4)))
            prev[pb.name] = pos.copy()
    return result

def main():
    print("=== Cinema Motion QA ===")
    print(scene_info())
    arms = find_armatures()
    if not arms:
        print("NG: Armature not found.")
        return
    for arm in arms:
        print(f"Armature: {arm.name}")
        jumps = detect_large_bone_jumps(arm)
        if jumps:
            print("WARN: Large bone jumps detected:")
            for item in jumps[:50]:
                print(item)
        else:
            print("OK: No large bone jumps detected with current threshold.")
    print("QA finished. Save console output to qa_report.md")

if __name__ == "__main__":
    main()
