# -*- coding: utf-8 -*-
"""Rollout renderer + machine-readable walk check.

学習済み方策を1環境でロールアウトし、(a) 追跡カメラのPNGフレーム、(b) walk_check.json
(final_travel / fell / min_upright / min_z) を出力する。数値ゲートを騙す「転倒して這う」
系のハックはここで検出される([T047]罠#7 — 目視チェックの自動化)。

env:
  WALK_CKPT: 方策チェックポイント(.pt)  default: C:\v50_work\stage_a_run8\latest.pt
  WALK_OUT : 出力ディレクトリ            default: C:\v50_work\walk_frames
  WALK_STEPS: 制御ステップ数             default: 400 (8 s at 50 Hz)
"""
import sys, os, json, math, re, torch
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import train_v50_walk_tracking as T
import genesis as gs

CKPT = os.environ.get("WALK_CKPT", r"C:\v50_work\stage_a_run8\latest.pt")
OUT = os.environ.get("WALK_OUT", r"C:\v50_work\walk_frames")
STEPS = int(os.environ.get("WALK_STEPS", "400"))
if os.environ.get("WALK_REF_JSON"):        # Stage B: 実モーション参照で評価
    T.load_reference(os.environ["WALK_REF_JSON"])
TERRAIN = os.environ.get("WALK_TERRAIN", "none")   # U6: 学習時と同じ地形で評価
os.makedirs(OUT, exist_ok=True)

# 罠#8対策: モデルXMLはトレーナの build_model_xml が唯一の正(複製XML禁止)
noact = os.path.join(OUT, "model.xml")
open(noact, "w", encoding="utf-8").write(T.build_model_xml(TERRAIN))

gs.init(backend=gs.gpu, logging_level="warning")
sc = gs.Scene(show_viewer=False, sim_options=gs.options.SimOptions(dt=T.DT_SIM, substeps=2))
robot = sc.add_entity(gs.morphs.MJCF(file=noact))
cam = sc.add_camera(res=(640, 480), pos=(3.0, 0.5, 0.6), lookat=(0.0, 0.0, 0.0), fov=40, GUI=False)
sc.build(n_envs=1)

dof_idx = [robot.get_joint(n).dof_idx_local for n in T.DOF_NAMES]
robot.set_dofs_kp(torch.tensor(T.KP, device="cuda"), dof_idx)
robot.set_dofs_kv(torch.tensor(T.KV, device="cuda"), dof_idx)

ac = T.ActorCritic().cuda()
ac.load_state_dict(torch.load(CKPT, weights_only=True))
print("policy:", CKPT)

qpos0 = robot.get_qpos().clone()
stand_z = 0.44
phase = torch.zeros(1, device="cuda")
prev_pos = qpos0[:, :3].clone(); prev_quat = qpos0[:, 3:7].clone()
lin_vel = torch.zeros(1, 3, device="cuda"); ang_vel = torch.zeros(1, 3, device="cuda")
steps = torch.zeros(1, device="cuda")
x0 = T.FWD_SIGN * qpos0[:, T.FWD_AXIS]
min_z, min_upright = 10.0, 1.0


def obs():
    q = robot.get_dofs_position(dof_idx); qd = robot.get_dofs_velocity(dof_idx)
    qp = robot.get_qpos(); pos = qp[:, :3]; quat = qp[:, 3:7]
    grav = T.quat_gravity(quat); ref = T.gait_reference(phase)
    tp = 2 * math.pi
    dt_ctrl = T.DT_SIM * T.DECIMATION
    x_err = (T.FWD_SIGN * pos[:, T.FWD_AXIS] - (x0 + steps * dt_ctrl * T.TARGET_VX))
    return torch.cat([q - ref, qd * 0.05, (pos[:, 2:3] - stand_z), lin_vel * 0.25,
                      ang_vel * 0.25, grav, torch.sin(phase * tp).unsqueeze(1),
                      torch.cos(phase * tp).unsqueeze(1),
                      (x_err * 0.5).clamp(-2, 2).unsqueeze(1),
                      torch.zeros(1, 1, device="cuda")], dim=1)


with torch.no_grad():
    o = obs()
    for step in range(STEPS):
        act = ac.actor(o)
        target = T.gait_reference(phase) + T.ACTION_SCALE * torch.tanh(act)
        robot.control_dofs_position(target, dof_idx)
        for _ in range(T.DECIMATION):
            sc.step()
        phase = (phase + T.DT_SIM * T.DECIMATION / T.GAIT_PERIOD) % 1.0
        steps += 1
        qp = robot.get_qpos()
        dt_c = T.DT_SIM * T.DECIMATION
        lin_vel = (qp[:, :3] - prev_pos) / dt_c
        ang_vel = T.quat_angvel(qp[:, 3:7], prev_quat, dt_c)
        prev_pos = qp[:, :3].clone(); prev_quat = qp[:, 3:7].clone()
        grav = T.quat_gravity(qp[:, 3:7])
        min_upright = min(min_upright, float((-grav[0, 2]).clamp(0, 1)))
        dz = float(T.terrain_dz(qp[:, T.FWD_AXIS], TERRAIN)[0])
        min_z = min(min_z, float(qp[0, 2]) - dz)   # 地形期待高さ差し引きの実効高
        o = obs()
        if step % 24 == 0 or step == STEPS - 1:
            y = qp[0, 1].item()
            cam.set_pose(pos=(3.0, y + 0.5, 0.6), lookat=(0.0, y, 0.0))
            rgb = cam.render(rgb=True)[0]
            from PIL import Image
            Image.fromarray(rgb).save(os.path.join(OUT, f"walk_{step:03d}.png"))

travel = float(T.FWD_SIGN * (qp[0, T.FWD_AXIS] - qpos0[0, T.FWD_AXIS]))
fell = (min_z < stand_z - 0.20) or (min_upright < 0.5)
check = {"schema": "clawstack.walk_check.v1", "ckpt": CKPT, "terrain": TERRAIN,
         "final_travel": round(travel, 3), "fell": fell,
         "min_z": round(min_z, 3), "min_upright": round(min_upright, 3),
         "steps": STEPS, "seconds": STEPS * T.DT_SIM * T.DECIMATION}
with open(os.path.join(OUT, "walk_check.json"), "w", encoding="utf-8") as f:
    json.dump(check, f, ensure_ascii=False, indent=2)
print("WALK_CHECK:", json.dumps(check, ensure_ascii=False))
print("final y travel:", round(travel, 3), "m")
