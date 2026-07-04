import sys, os, torch
sys.path.insert(0, r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\stage_a")
import train_v50_walk_tracking as T
import genesis as gs

OUT = r"C:\v50_work\walk_frames"
os.makedirs(OUT, exist_ok=True)

# 1-env scene with an offscreen camera
xml = open(T.MJCF_SRC, encoding="utf-8").read()
import re
xml = re.sub(r"<actuator>.*?</actuator>", "", xml, flags=re.S)
xml = xml.replace('fromto="0 0 0 0.15 0 -0.05"', 'fromto="0 0.06 -0.05 0 -0.15 -0.05"')
xml = xml.replace('pos="0.15 0 -0.08"', 'pos="0 -0.15 -0.08"')
xml = re.sub(r'(<geom name="foot_(L|R)_contact"[^>]*/>)',
             r'\1<geom name="foot_\2_heel" type="sphere" size="0.04" pos="0 0.06 -0.08" condim="6" friction="1.5 0.01 0.001"/>', xml)
noact = os.path.join(OUT, "model.xml")
open(noact, "w", encoding="utf-8").write(xml)

gs.init(backend=gs.gpu, logging_level="warning")
sc = gs.Scene(show_viewer=False, sim_options=gs.options.SimOptions(dt=T.DT_SIM, substeps=2))
robot = sc.add_entity(gs.morphs.MJCF(file=noact))
cam = sc.add_camera(res=(640, 480), pos=(3.0, 0.5, 0.6), lookat=(0.0, 0.0, 0.0), fov=40, GUI=False)
sc.build(n_envs=1)

dof_idx=[robot.get_joint(n).dof_idx_local for n in T.DOF_NAMES]
robot.set_dofs_kp(torch.tensor(T.KP, device="cuda"), dof_idx)
robot.set_dofs_kv(torch.tensor(T.KV, device="cuda"), dof_idx)

ac = T.ActorCritic().cuda()
import glob
ckpt = r"C:\v50_work\stage_a_run8\latest.pt"
if not os.path.exists(ckpt): ckpt = r"C:\v50_work\stage_a_run6\best.pt"
ac.load_state_dict(torch.load(ckpt, weights_only=True))
print("policy:", ckpt)

# lightweight env-like rollout (mirror of Env.step for 1 env)
qpos0 = robot.get_qpos().clone()
phase = torch.zeros(1, device="cuda")
prev_pos = qpos0[:, :3].clone(); prev_quat = qpos0[:, 3:7].clone()
lin_vel = torch.zeros(1,3,device="cuda"); ang_vel = torch.zeros(1,3,device="cuda")
steps = torch.zeros(1, device="cuda"); x0 = T.FWD_SIGN*qpos0[:, T.FWD_AXIS]
stand_z = 0.44
import math
def obs():
    q = robot.get_dofs_position(dof_idx); qd = robot.get_dofs_velocity(dof_idx)
    qp = robot.get_qpos(); pos=qp[:, :3]; quat=qp[:, 3:7]
    grav = T.quat_gravity(quat); ref = T.gait_reference(phase)
    two_pi = 2*math.pi
    dt_ctrl = T.DT_SIM*T.DECIMATION
    x_err = (T.FWD_SIGN*pos[:, T.FWD_AXIS] - (x0 + steps*dt_ctrl*T.TARGET_VX))
    return torch.cat([q-ref, qd*0.05, (pos[:,2:3]-stand_z), lin_vel*0.25, ang_vel*0.25, grav,
                      torch.sin(phase*two_pi).unsqueeze(1), torch.cos(phase*two_pi).unsqueeze(1),
                      (x_err*0.5).clamp(-2,2).unsqueeze(1), torch.zeros(1,1,device="cuda")], dim=1)

with torch.no_grad():
    o = obs()
    for step in range(240):   # 4.8 s
        act = ac.actor(o)
        target = T.gait_reference(phase) + T.ACTION_SCALE*torch.tanh(act)
        robot.control_dofs_position(target, dof_idx)
        for _ in range(T.DECIMATION): sc.step()
        phase = (phase + T.DT_SIM*T.DECIMATION/T.GAIT_PERIOD) % 1.0
        steps += 1
        qp = robot.get_qpos()
        dt_c = T.DT_SIM*T.DECIMATION
        lin_vel = (qp[:, :3]-prev_pos)/dt_c; ang_vel = T.quat_angvel(qp[:,3:7], prev_quat, dt_c)
        prev_pos = qp[:, :3].clone(); prev_quat = qp[:,3:7].clone()
        o = obs()
        if step % 24 == 0:
            # track the robot with the camera
            y = qp[0, 1].item()
            cam.set_pose(pos=(3.0, y+0.5, 0.6), lookat=(0.0, y, 0.0))
            rgb = cam.render(rgb=True)[0]
            from PIL import Image
            Image.fromarray(rgb).save(os.path.join(OUT, f"walk_{step:03d}.png"))
    print("final y travel:", round((T.FWD_SIGN*(qp[0, T.FWD_AXIS]-qpos0[0, T.FWD_AXIS])).item(), 3), "m")
print("frames in", OUT)
