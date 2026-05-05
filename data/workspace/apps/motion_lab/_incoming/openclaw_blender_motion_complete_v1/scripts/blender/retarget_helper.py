"""
Blender用リターゲット補助スクリプト雛形。
BlenderのText Editorまたは --python で実行。
注意：これは安全な雛形です。実案件ではボーン名を確認してから使ってください。
"""
import bpy
from pathlib import Path

DRY_RUN = True

BASIC_BONE_MAP = {
    "Hips": "hips",
    "Spine": "spine",
    "Spine1": "chest",
    "Neck": "neck",
    "Head": "head",
    "LeftArm": "left_upper_arm",
    "LeftForeArm": "left_lower_arm",
    "LeftHand": "left_hand",
    "RightArm": "right_upper_arm",
    "RightForeArm": "right_lower_arm",
    "RightHand": "right_hand",
    "LeftUpLeg": "left_upper_leg",
    "LeftLeg": "left_lower_leg",
    "LeftFoot": "left_foot",
    "RightUpLeg": "right_upper_leg",
    "RightLeg": "right_lower_leg",
    "RightFoot": "right_foot",
}


def list_armatures():
    return [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]


def print_armature_bones(armature):
    print(f"ARMATURE: {armature.name}")
    for bone in armature.data.bones:
        print(" -", bone.name)


def create_report():
    arms = list_armatures()
    print("=== Retarget Helper Report ===")
    print("Armature count:", len(arms))
    for arm in arms:
        print_armature_bones(arm)
    print("DRY_RUN:", DRY_RUN)


def main():
    create_report()
    if DRY_RUN:
        print("Dry-run only. No changes applied.")
        return
    # 実リターゲット処理は環境・アドオンに依存するため、Codexがボーン名確認後に実装する。

if __name__ == "__main__":
    main()
