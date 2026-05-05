"""
FBX/BVHモーション一括インポート雛形。
raw_motion_dir を指定し、Blenderへ取り込む。
既存ファイル上書き禁止。まずDRY_RUN=Trueで確認。
"""
import bpy
from pathlib import Path

DRY_RUN = True
raw_motion_dir = Path(r"D:/Clawdbot_Docker_20260125/clawstack_v2/extensions/blender_motion_pipeline/assets/motions/raw")


def import_fbx(path: Path):
    print(f"Import FBX: {path}")
    if not DRY_RUN:
        bpy.ops.import_scene.fbx(filepath=str(path))


def import_bvh(path: Path):
    print(f"Import BVH: {path}")
    if not DRY_RUN:
        bpy.ops.import_anim.bvh(filepath=str(path), global_scale=1.0)


def main():
    if not raw_motion_dir.exists():
        print("Motion directory not found:", raw_motion_dir)
        return
    files = list(raw_motion_dir.glob("*.fbx")) + list(raw_motion_dir.glob("*.bvh"))
    print("Found motion files:", len(files))
    for f in files:
        if f.suffix.lower() == ".fbx":
            import_fbx(f)
        elif f.suffix.lower() == ".bvh":
            import_bvh(f)
    if DRY_RUN:
        print("Dry-run only. Set DRY_RUN=False after review.")

if __name__ == "__main__":
    main()
