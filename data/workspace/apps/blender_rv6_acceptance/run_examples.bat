@echo off
chcp 65001
echo Mini PC Blender RV6 Acceptance Harness examples
python scripts	ask_gate.py --task real_3d_video --config configscceptance_policy.yaml
python scripts	ask_gate.py --task dxf_to_step --config configscceptance_policy.yaml
echo blender --background your_scene.blend --python scriptslender_city_camera_rv6_prep.py
echo python scripts\watchdog_repair_gate.py --command "python your_task.py"
pause
