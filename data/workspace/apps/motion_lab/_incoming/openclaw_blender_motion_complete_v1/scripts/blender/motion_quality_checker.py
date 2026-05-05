"""
モーション品質チェック雛形。
対象：足滑り、手の高さ、フレーム範囲などの検査を追加するための土台。
"""
import bpy

FOOT_KEYWORDS = ["foot", "toe", "ankle", "LeftFoot", "RightFoot", "左足", "右足"]
HAND_KEYWORDS = ["hand", "LeftHand", "RightHand", "左手", "右手"]


def find_pose_bones_by_keywords(armature, keywords):
    result = []
    for pb in armature.pose.bones:
        low = pb.name.lower()
        if any(k.lower() in low for k in keywords):
            result.append(pb.name)
    return result


def main():
    arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    print("=== Motion Quality Checker ===")
    for arm in arms:
        print("Armature:", arm.name)
        print("Foot candidates:", find_pose_bones_by_keywords(arm, FOOT_KEYWORDS))
        print("Hand candidates:", find_pose_bones_by_keywords(arm, HAND_KEYWORDS))
    print("次工程：接地フレーム検出、足滑り距離、手めり込み判定を実装してください。")

if __name__ == "__main__":
    main()
