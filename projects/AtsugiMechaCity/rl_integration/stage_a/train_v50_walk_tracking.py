# -*- coding: utf-8 -*-
"""Stage A: V50 walk tracking on Genesis GPU (self-contained PPO).

Goal (bd 1wr / decision doc Stage A): produce a physically-valid walk with real
forward travel, replacing the near-zero-amplitude sin reference. The reference
JSON (v50_ref_motion.json) was found broken (root travel 0.0, hip amplitude
~0.5 deg), so this trainer generates its own analytic sin-gait reference with
the amplitudes the Blender preview actually uses (hip 11deg / knee 10deg /
ankle 5deg) plus a forward-velocity target of 0.8 m/s (v50_amp_config.yaml).

Design notes:
- Self-contained PPO (no rsl-rl) to avoid library API drift; single file so a
  local model can maintain it (API-fuel rule 2).
- Genesis API verified by C:\\v50_work\\genesis_api_probe.py on genesis 1.2.1.
- Residual action space: PD target = reference pose + 0.35 * action.

Run (venv: C:\\v50_work\\genesis_venv):
  python train_v50_walk_tracking.py --iterations 60 --n-envs 256 --out C:\\v50_work\\stage_a_smoke
"""
import argparse, json, math, os, re, time
import torch
import torch.nn as nn

MJCF_SRC = r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\artifacts\v50_mecha.xml"
DOF_NAMES = ["hip_L","knee_L","ankle_L","hip_R","knee_R","ankle_R",
             "shoulder_L","elbow_L","wrist_L","shoulder_R","elbow_R","wrist_R"]
# PD gains per DOF (v50_amp_config.yaml). MJCF <actuator> is stripped at load:
# Genesis imports MJCF position actuators as non-PD-reducible act_gain/act_bias that
# FIGHT control_dofs_position (probe finding, 2026-07-03); explicit kp/kv instead.
KP = [400., 300., 200., 400., 300., 200., 200., 150., 80., 200., 150., 80.]
KV = [40., 30., 20., 40., 30., 20., 20., 15., 8., 20., 15., 8.]
DT_SIM = 0.002
DECIMATION = 10         # control at 50 Hz
# run3 (INC-141): 0.8 m/s was kinematically unreachable for the 11-deg sin gait
# (stride-limited max ~0.24 m/s) -> the travel reward died within 2 s and the
# policy settled into marching in place (run1, run2). Curriculum: reachable
# target with a longer/faster stride first; raise speed later.
GAIT_PERIOD = 1.2       # seconds per gait cycle
TARGET_VX = 0.25        # m/s forward along FWD_AXIS
# INC-141 trap #6 (user caught it): hips are separated along X => X is the
# LATERAL axis and sagittal hip swing (about X) moves the legs in the Y-Z plane,
# so walking direction is +Y. Runs 1-4 rewarded velocity along X (sideways).
# The exporter also put the TOES along +X (sideways feet); the XML rewrite in
# Env.__init__ rotates foot geoms to point +Y.
FWD_AXIS = 1            # 0=x, 1=y
# Dev probe: the gait naturally propels at -0.5..-1.0 m/s along -Y, and the
# Blender V50 also faces -Y (front camera sits at -Y). Forward = -Y.
FWD_SIGN = -1.0
ACTION_SCALE = 0.35
EP_LEN = 400            # 8 s
OBS_DIM = 38
ACT_DIM = 12


def gait_reference(phase):
    """phase (N,) in [0,1) -> reference joint targets (N,12) in radians.
    Amplitudes mirror v50_final_walk_preview.py (11/10/5 deg) + arm counterswing."""
    two_pi = 2.0 * math.pi
    s = torch.sin(phase * two_pi)
    hip_l = 0.30 * s                                 # 17 deg (run3: longer stride)
    hip_r = -0.30 * s
    knee_l = 0.26 * torch.clamp(-s, min=0.0)         # 15 deg, stance-flex
    knee_r = 0.26 * torch.clamp(s, min=0.0)
    ank_l = -0.12 * torch.clamp(-s, min=0.0)         # 7 deg
    ank_r = -0.12 * torch.clamp(s, min=0.0)
    sh_l = -0.18 * s                                 # counter-phase arm swing
    sh_r = 0.18 * s
    elb = torch.full_like(s, -0.15)                  # slight constant elbow bend
    wr = torch.zeros_like(s)
    return torch.stack([hip_l, knee_l, ank_l, hip_r, knee_r, ank_r,
                        sh_l, elb, wr, sh_r, elb, wr], dim=1)


def quat_angvel(q, q_prev, dt):
    """Approximate world-frame angular velocity from consecutive quats (wxyz)."""
    # r = q * conj(q_prev); omega ~= 2 * r.xyz / dt  (small-angle)
    w1, x1, y1, z1 = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
    w2, x2, y2, z2 = q_prev[:, 0], -q_prev[:, 1], -q_prev[:, 2], -q_prev[:, 3]
    rw = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    rx = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    ry = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    rz = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    sign = torch.where(rw < 0, -1.0, 1.0).unsqueeze(1)
    return sign * 2.0 * torch.stack([rx, ry, rz], dim=1) / dt


def quat_gravity(quat):
    """(N,4) wxyz -> gravity direction in body frame (N,3); upright => (0,0,-1)."""
    w, x, y, z = quat[:, 0], quat[:, 1], quat[:, 2], quat[:, 3]
    # R^T @ [0,0,-1] = third row of R negated per column -> compute directly
    gx = -(2 * (x * z - w * y))
    gy = -(2 * (y * z + w * x))
    gz = -(1 - 2 * (x * x + y * y))
    return torch.stack([gx, gy, gz], dim=1)


class Env:
    def __init__(self, n_envs, out_dir):
        import genesis as gs
        self.gs = gs
        # strip <actuator> (see KP/KV comment); robot stands on the MJCF's own floor
        # plane at z=-0.92 — do NOT add another plane (feet-buried-spawn bug).
        xml = open(MJCF_SRC, encoding="utf-8").read()
        xml = re.sub(r"<actuator>.*?</actuator>", "", xml, flags=re.S)
        # trap #6 fix: exporter put toes on +X (sideways). Anatomical forward is -Y
        # (Blender front camera sits at -Y; hips separate along X). Foot becomes a
        # flat heel-to-toe capsule along Y plus toe AND heel contact spheres —
        # dev5/dev6 showed the untrained robot always tips toward the side with no
        # foot lever (heel), so a heel kills that fall bias.
        xml = xml.replace('fromto="0 0 0 0.15 0 -0.05"',
                          'fromto="0 0.06 -0.05 0 -0.15 -0.05"')
        xml = xml.replace('pos="0.15 0 -0.08"', 'pos="0 -0.15 -0.08"')
        xml = re.sub(r'(<geom name="foot_(L|R)_contact"[^>]*/>)',
                     r'\1<geom name="foot_\2_heel" type="sphere" size="0.04" '
                     r'pos="0 0.06 -0.08" condim="6" friction="1.5 0.01 0.001"/>',
                     xml)
        noact = os.path.join(out_dir, "v50_mecha_noact.xml")
        with open(noact, "w", encoding="utf-8") as f:
            f.write(xml)
        gs.init(backend=gs.gpu, logging_level="warning")
        self.scene = gs.Scene(show_viewer=False,
                              sim_options=gs.options.SimOptions(dt=DT_SIM, substeps=2))
        self.robot = self.scene.add_entity(gs.morphs.MJCF(file=noact))
        self.scene.build(n_envs=n_envs)
        self.n = n_envs
        self.dof_idx = [self.robot.get_joint(nm).dof_idx_local for nm in DOF_NAMES]
        dev = "cuda"
        self.robot.set_dofs_kp(torch.tensor(KP, device=dev), self.dof_idx)
        self.robot.set_dofs_kv(torch.tensor(KV, device=dev), self.dof_idx)
        self.qpos0 = self.robot.get_qpos().clone()          # native spawn (N,19)
        # settle to find true standing height (contact equilibrium)
        for _ in range(300):
            self.scene.step()
        self.stand_z = float(self.robot.get_qpos()[:, 2].mean())
        self.phase = torch.rand(n_envs, device=dev)
        self.steps = torch.zeros(n_envs, device=dev, dtype=torch.long)
        self.x0 = torch.zeros(n_envs, device=dev)           # root x at episode start
        # INC-141 trap #4: get_vel()/get_ang() (and links_vel) return zeros for this
        # MJCF articulated entity in genesis 1.2.1 — all three runs trained with a
        # blind/zero velocity signal. Velocities are now finite-differenced from
        # get_qpos() (the only getter verified to report true world state).
        self.lin_vel = torch.zeros(n_envs, 3, device=dev)
        self.ang_vel = torch.zeros(n_envs, 3, device=dev)
        self.prev_pos = torch.zeros(n_envs, 3, device=dev)
        self.prev_quat = torch.zeros(n_envs, 4, device=dev)
        self.reset(torch.arange(n_envs, device=dev))

    def reset(self, idx):
        if idx.numel() == 0:
            return
        self.robot.set_qpos(self.qpos0[idx], envs_idx=idx, zero_velocity=True)
        self.phase[idx] = torch.rand(idx.numel(), device="cuda")
        ref = gait_reference(self.phase[idx])
        self.robot.set_dofs_position(ref, dofs_idx_local=self.dof_idx, envs_idx=idx,
                                     zero_velocity=True)
        self.steps[idx] = 0
        qpos = self.robot.get_qpos()
        self.x0[idx] = FWD_SIGN * qpos[idx, FWD_AXIS]
        self.prev_pos[idx] = qpos[idx, :3]
        self.prev_quat[idx] = qpos[idx, 3:7]
        self.lin_vel[idx] = 0.0
        self.ang_vel[idx] = 0.0

    def root_state(self):
        qpos = self.robot.get_qpos()
        return qpos[:, :3], qpos[:, 3:7]                    # world pos, quat (wxyz)

    def obs(self):
        q = self.robot.get_dofs_position(self.dof_idx)
        qd = self.robot.get_dofs_velocity(self.dof_idx)
        pos, quat = self.root_state()
        vel = self.lin_vel
        ang = self.ang_vel
        grav = quat_gravity(quat)
        ref = gait_reference(self.phase)
        two_pi = 2.0 * math.pi
        dt_ctrl = DT_SIM * DECIMATION
        x_err = (FWD_SIGN * pos[:, FWD_AXIS] - (self.x0 + self.steps.float() * dt_ctrl * TARGET_VX))
        return torch.cat([
            q - ref,                       # 12 pose error
            qd * 0.05,                     # 12
            (pos[:, 2:3] - self.stand_z),  # 1
            vel * 0.25,                    # 3
            ang * 0.25,                    # 3
            grav,                          # 3
            torch.sin(self.phase * two_pi).unsqueeze(1),
            torch.cos(self.phase * two_pi).unsqueeze(1),
            (x_err * 0.5).clamp(-2, 2).unsqueeze(1),  # forward-progress error
            torch.zeros(self.n, 1, device="cuda"),    # reserved (skill embed slot)
        ], dim=1)

    def step(self, action):
        ref = gait_reference(self.phase)
        target = ref + ACTION_SCALE * torch.tanh(action)
        self.robot.control_dofs_position(target, self.dof_idx)
        for _ in range(DECIMATION):
            self.scene.step()
        self.phase = (self.phase + DT_SIM * DECIMATION / GAIT_PERIOD) % 1.0
        self.steps += 1

        q = self.robot.get_dofs_position(self.dof_idx)
        pos, quat = self.root_state()
        dt_c = DT_SIM * DECIMATION
        self.lin_vel = (pos - self.prev_pos) / dt_c
        self.ang_vel = quat_angvel(quat, self.prev_quat, dt_c)
        self.prev_pos = pos.clone()
        self.prev_quat = quat.clone()
        vel = self.lin_vel
        ang = self.ang_vel
        grav = quat_gravity(quat)

        pose_err = ((q - ref) ** 2).mean(dim=1)
        r_pose = torch.exp(-8.0 * pose_err)
        # INC-141 follow-up: exp velocity reward let the policy settle into
        # marching-in-place (vx=0 local optimum, run1). Linear velocity reward has
        # a clear forward gradient at vx=0, and root-position tracking (DeepMimic
        # convention) pays continuously for actual travel.
        upright = (-grav[:, 2]).clamp(0.0, 1.0)          # 1 when upright
        # trap #7 (reward hacking, run7 visual check): ungated velocity reward let
        # the policy dive forward and CRAWL for speed. Velocity/travel only pay
        # while upright (x upright^2), and falling costs more (-5, tighter tilt cut).
        gate = upright ** 2
        # run10: plateau-shaped velocity reward peaking AT the target pace.
        # History: linear->sprint 0.4 & fall at 2s (run8); hard cap->freeze at
        # 0.05 (run9). A peak at 0.25 penalizes both idling and overspeed while
        # keeping a dense gradient from either side.
        fwd_v = FWD_SIGN * vel[:, FWD_AXIS]
        r_vel = torch.exp(-10.0 * (fwd_v - TARGET_VX) ** 2) * gate
        dt_ctrl = DT_SIM * DECIMATION
        x_expect = self.x0 + self.steps.float() * dt_ctrl * TARGET_VX
        r_travel = torch.exp(-2.0 * (FWD_SIGN * pos[:, FWD_AXIS] - x_expect) ** 2) * gate
        r_up = upright
        pen_act = (action ** 2).mean(dim=1)
        pen_ang = (ang ** 2).sum(dim=1)
        reward = 0.8 * r_pose + 1.5 * r_vel + 1.0 * r_travel + 0.5 * r_up + 0.25 \
                 - 0.01 * pen_act - 0.02 * pen_ang

        fallen = (pos[:, 2] < self.stand_z - 0.25) | (upright < 0.65)
        timeout = self.steps >= EP_LEN
        done = fallen | timeout
        reward = torch.where(fallen, reward - 5.0, reward)

        idx = torch.nonzero(done).squeeze(-1)
        metrics = {"vx": (FWD_SIGN * vel[:, FWD_AXIS]).mean().item(), "up": upright.mean().item(),
                   "pose_err": pose_err.mean().item(), "falls": fallen.float().sum().item()}
        self.reset(idx)
        return self.obs(), reward, done, metrics


class ActorCritic(nn.Module):
    def __init__(self):
        super().__init__()
        def mlp(out):
            return nn.Sequential(nn.Linear(OBS_DIM, 256), nn.ELU(),
                                 nn.Linear(256, 128), nn.ELU(), nn.Linear(128, out))
        self.actor = mlp(ACT_DIM)
        self.critic = mlp(1)
        self.log_std = nn.Parameter(torch.full((ACT_DIM,), -0.7))

    def dist(self, obs):
        return torch.distributions.Normal(self.actor(obs), self.log_std.exp())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=60)
    ap.add_argument("--n-envs", type=int, default=256)
    ap.add_argument("--rollout", type=int, default=32)
    ap.add_argument("--out", default=r"C:\v50_work\stage_a_smoke")
    ap.add_argument("--resume", default=None)
    # run6: anneal exploration so the walk consolidates into the deterministic
    # mean (run5 walked at +0.14 stochastically but +0.02 deterministically —
    # noise-driven propulsion).
    ap.add_argument("--entropy", type=float, default=0.005)
    ap.add_argument("--init-log-std", type=float, default=None)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    env = Env(args.n_envs, args.out)
    ac = ActorCritic().cuda()
    if args.resume:
        ac.load_state_dict(torch.load(args.resume, weights_only=True))
    if args.init_log_std is not None:
        with torch.no_grad():
            ac.log_std.fill_(args.init_log_std)
    opt = torch.optim.Adam(ac.parameters(), lr=3e-4)
    obs = env.obs()
    N, T = args.n_envs, args.rollout
    gamma, lam, clip = 0.99, 0.95, 0.2
    best = -1e9
    t_start = time.time()

    for it in range(1, args.iterations + 1):
        buf_obs = torch.zeros(T, N, OBS_DIM, device="cuda")
        buf_act = torch.zeros(T, N, ACT_DIM, device="cuda")
        buf_logp = torch.zeros(T, N, device="cuda")
        buf_rew = torch.zeros(T, N, device="cuda")
        buf_done = torch.zeros(T, N, device="cuda")
        buf_val = torch.zeros(T + 1, N, device="cuda")
        m_acc = {"vx": 0.0, "up": 0.0, "pose_err": 0.0, "falls": 0.0}
        with torch.no_grad():
            for t in range(T):
                dist = ac.dist(obs)
                act = dist.sample()
                buf_obs[t] = obs; buf_act[t] = act
                buf_logp[t] = dist.log_prob(act).sum(-1)
                buf_val[t] = ac.critic(obs).squeeze(-1)
                obs, rew, done, m = env.step(act)
                buf_rew[t] = rew; buf_done[t] = done.float()
                for k in m_acc: m_acc[k] += m[k] / T
            buf_val[T] = ac.critic(obs).squeeze(-1)
            adv = torch.zeros(T, N, device="cuda"); gae = 0
            for t in reversed(range(T)):
                nd = 1.0 - buf_done[t]
                delta = buf_rew[t] + gamma * buf_val[t + 1] * nd - buf_val[t]
                gae = delta + gamma * lam * nd * gae
                adv[t] = gae
            ret = adv + buf_val[:T]
            adv = (adv - adv.mean()) / (adv.std() + 1e-8)

        b_obs = buf_obs.reshape(-1, OBS_DIM); b_act = buf_act.reshape(-1, ACT_DIM)
        b_logp = buf_logp.reshape(-1); b_adv = adv.reshape(-1); b_ret = ret.reshape(-1)
        n_batch = b_obs.shape[0]
        for _ in range(4):
            perm = torch.randperm(n_batch, device="cuda")
            for mb in perm.chunk(4):
                dist = ac.dist(b_obs[mb])
                logp = dist.log_prob(b_act[mb]).sum(-1)
                ratio = (logp - b_logp[mb]).exp()
                s1 = ratio * b_adv[mb]
                s2 = torch.clamp(ratio, 1 - clip, 1 + clip) * b_adv[mb]
                loss_pi = -torch.min(s1, s2).mean()
                loss_v = ((ac.critic(b_obs[mb]).squeeze(-1) - b_ret[mb]) ** 2).mean()
                loss = loss_pi + 0.5 * loss_v - args.entropy * dist.entropy().sum(-1).mean()
                opt.zero_grad(); loss.backward()
                nn.utils.clip_grad_norm_(ac.parameters(), 1.0)
                opt.step()

        mean_rew = buf_rew.mean().item()
        print(f"it {it:4d} | rew/step {mean_rew:6.3f} | vx {m_acc['vx']:5.2f} | "
              f"up {m_acc['up']:4.2f} | pose_err {m_acc['pose_err']:.4f} | falls {m_acc['falls']:.0f}",
              flush=True)
        if mean_rew > best:
            best = mean_rew
            torch.save(ac.state_dict(), os.path.join(args.out, "best.pt"))
        if it % 10 == 0 or it == args.iterations:
            torch.save(ac.state_dict(), os.path.join(args.out, "latest.pt"))
            with open(os.path.join(args.out, "status.json"), "w", encoding="utf-8") as f:
                json.dump({"schema": "clawstack.stage_a_walk_tracking.v1",
                           "iteration": it, "iterations_total": args.iterations,
                           "mean_reward_per_step": round(mean_rew, 4),
                           "best_reward_per_step": round(best, 4),
                           "vx_mean": round(m_acc["vx"], 3), "upright": round(m_acc["up"], 3),
                           "pose_err": round(m_acc["pose_err"], 5),
                           "elapsed_sec": round(time.time() - t_start, 1),
                           "n_envs": N}, f, indent=2)

    # eval: forward travel over 400 control steps (8 s), deterministic AND
    # stochastic (run5 walked only with exploration noise — measure both).
    eval_res = {"target_vx": TARGET_VX,
                "note": "travel is lower bound (env auto-resets on falls)"}
    with torch.no_grad():
        for mode in ("deterministic", "stochastic"):
            env.reset(torch.arange(N, device="cuda"))
            obs_e = env.obs()
            x0 = (FWD_SIGN * env.robot.get_qpos()[:, FWD_AXIS]).clone()
            vx_acc = 0.0
            for _ in range(EP_LEN):
                act = ac.actor(obs_e) if mode == "deterministic" else ac.dist(obs_e).sample()
                obs_e, _, _, m = env.step(act)
                vx_acc += m["vx"] / EP_LEN
            travel = (FWD_SIGN * env.robot.get_qpos()[:, FWD_AXIS] - x0).mean().item()
            eval_res[f"{mode}_travel_m_8s"] = round(travel, 3)
            eval_res[f"{mode}_vx_mean"] = round(vx_acc, 3)
    eval_res["eval_forward_travel_m_8s"] = eval_res["deterministic_travel_m_8s"]
    eval_res["eval_vx_mean"] = eval_res["deterministic_vx_mean"]
    with open(os.path.join(args.out, "eval.json"), "w", encoding="utf-8") as f:
        json.dump(eval_res, f, indent=2)
    print("EVAL:", json.dumps(eval_res))
    print("DONE")


if __name__ == "__main__":
    main()
