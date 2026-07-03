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
GAIT_PERIOD = 1.6       # seconds per gait cycle
TARGET_VX = 0.8         # m/s forward (+x is model forward per preview root drift)
ACTION_SCALE = 0.35
EP_LEN = 400            # 8 s
OBS_DIM = 38
ACT_DIM = 12


def gait_reference(phase):
    """phase (N,) in [0,1) -> reference joint targets (N,12) in radians.
    Amplitudes mirror v50_final_walk_preview.py (11/10/5 deg) + arm counterswing."""
    two_pi = 2.0 * math.pi
    s = torch.sin(phase * two_pi)
    hip_l = 0.192 * s                                # 11 deg
    hip_r = -0.192 * s
    knee_l = 0.175 * torch.clamp(-s, min=0.0)        # 10 deg, stance-flex
    knee_r = 0.175 * torch.clamp(s, min=0.0)
    ank_l = -0.087 * torch.clamp(-s, min=0.0)        # 5 deg
    ank_r = -0.087 * torch.clamp(s, min=0.0)
    sh_l = -0.12 * s                                 # counter-phase arm swing
    sh_r = 0.12 * s
    elb = torch.full_like(s, -0.15)                  # slight constant elbow bend
    wr = torch.zeros_like(s)
    return torch.stack([hip_l, knee_l, ank_l, hip_r, knee_r, ank_r,
                        sh_l, elb, wr, sh_r, elb, wr], dim=1)


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
        noact = os.path.join(out_dir, "v50_mecha_noact.xml")
        with open(noact, "w", encoding="utf-8") as f:
            f.write(re.sub(r"<actuator>.*?</actuator>", "", xml, flags=re.S))
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

    def root_state(self):
        qpos = self.robot.get_qpos()
        return qpos[:, :3], qpos[:, 3:7]                    # world pos, quat (wxyz)

    def obs(self):
        q = self.robot.get_dofs_position(self.dof_idx)
        qd = self.robot.get_dofs_velocity(self.dof_idx)
        pos, quat = self.root_state()
        vel = self.robot.get_vel()
        ang = self.robot.get_ang()
        grav = quat_gravity(quat)
        ref = gait_reference(self.phase)
        two_pi = 2.0 * math.pi
        return torch.cat([
            q - ref,                       # 12 pose error
            qd * 0.05,                     # 12
            (pos[:, 2:3] - self.stand_z),  # 1
            vel * 0.25,                    # 3
            ang * 0.25,                    # 3
            grav,                          # 3
            torch.sin(self.phase * two_pi).unsqueeze(1),
            torch.cos(self.phase * two_pi).unsqueeze(1),
            torch.zeros(self.n, 2, device="cuda"),  # reserved (skill embed slot)
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
        vel = self.robot.get_vel()
        ang = self.robot.get_ang()
        grav = quat_gravity(quat)

        pose_err = ((q - ref) ** 2).mean(dim=1)
        r_pose = torch.exp(-8.0 * pose_err)
        r_vel = torch.exp(-4.0 * (vel[:, 0] - TARGET_VX) ** 2)
        upright = (-grav[:, 2]).clamp(0.0, 1.0)          # 1 when upright
        r_up = upright
        pen_act = (action ** 2).mean(dim=1)
        pen_ang = (ang ** 2).sum(dim=1)
        reward = 1.2 * r_pose + 1.5 * r_vel + 0.5 * r_up + 0.25 \
                 - 0.01 * pen_act - 0.02 * pen_ang

        fallen = (pos[:, 2] < self.stand_z - 0.25) | (upright < 0.5)
        timeout = self.steps >= EP_LEN
        done = fallen | timeout
        reward = torch.where(fallen, reward - 2.0, reward)

        idx = torch.nonzero(done).squeeze(-1)
        metrics = {"vx": vel[:, 0].mean().item(), "up": upright.mean().item(),
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
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    env = Env(args.n_envs, args.out)
    ac = ActorCritic().cuda()
    if args.resume:
        ac.load_state_dict(torch.load(args.resume, weights_only=True))
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
                loss = loss_pi + 0.5 * loss_v - 0.005 * dist.entropy().sum(-1).mean()
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

    # deterministic eval: forward travel over 400 control steps (8 s)
    with torch.no_grad():
        env.reset(torch.arange(N, device="cuda"))
        obs_e = env.obs()
        x0 = env.robot.get_qpos()[:, 0].clone()
        vx_acc = 0.0
        for _ in range(EP_LEN):
            act = ac.actor(obs_e)
            obs_e, _, _, m = env.step(act)
            vx_acc += m["vx"] / EP_LEN
        travel = (env.robot.get_qpos()[:, 0] - x0).mean().item()
    eval_res = {"eval_forward_travel_m_8s": round(travel, 3),
                "eval_vx_mean": round(vx_acc, 3),
                "target_vx": TARGET_VX,
                "note": "travel is lower bound (env auto-resets on falls)"}
    with open(os.path.join(args.out, "eval.json"), "w", encoding="utf-8") as f:
        json.dump(eval_res, f, indent=2)
    print("EVAL:", json.dumps(eval_res))
    print("DONE")


if __name__ == "__main__":
    main()
