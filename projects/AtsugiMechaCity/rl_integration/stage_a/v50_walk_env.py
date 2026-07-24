# -*- coding: utf-8 -*-
"""V50 walk environment (rsl_rl VecEnv) — contact-aware locomotion rewards.

WHY THIS FILE EXISTS
--------------------
`train_v50_walk_tracking.py` (self-contained PPO) has oscillated between two
degenerate attractors since 2026-07-20 and has not improved:

  walks_then_falls  (travel 1.4-1.85 m, falls at 4-7 s)
   <-> stand_freeze (travel 0.15-0.8 m, never falls)

Root causes identified 2026-07-23 by auditing that trainer against the
state of the art (legged_gym / rsl_rl / Genesis official Go2 example /
"Revisiting Reward Design ... for Robust Humanoid Standing and Walking",
arXiv:2404.19173):

  C1  NO CONTACT SIGNAL AT ALL. The single reward family that is known to
      break the stand/march-in-place local optimum -- `feet_air_time`
      (legged_gym) -- and the single term reported as the most reliable way
      to get walking instead of hopping -- single-foot-contact
      (arXiv:2404.19173) -- were both absent. The policy had no way to be
      paid for *stepping*, only for *moving*, so "don't move" and "lunge"
      were the only two basins.
  C2  TIMEOUT TREATED AS TERMINAL. GAE used `nd = 1 - done` with
      `done = fallen | timeout`, so the 8 s episode boundary cut value
      bootstrapping. Long-horizon walking was systematically undervalued.
      rsl_rl fixes this via `extras["time_outs"]`.
  C3  NO OBSERVATION NORMALIZATION. 46 raw dims spanning ~1e-2..1e1 fed
      straight to an MLP. rsl_rl's EmpiricalNormalization handles this.
  C4  GUARANTEED STANDING INCOME. `+0.1 constant + 0.3*r_up + 0.8*r_pose`
      paid ~1.2/step for standing still; measured mean reward was ~1.97,
      i.e. ~60% of the achieved return was freeze income.
  C5  NO PREVIOUS ACTION IN OBS and no action-rate penalty (only action
      magnitude). Both are standard in every modern locomotion stack and are
      what produce smooth, non-chattering gaits.
  C6  TRACKING SIGMA FAR TOO WIDE for a 0.25 m/s target: exp(-e^2/0.25) pays
      0.78 for standing completely still against a 0.25 m/s command.

PROBED FACTS (genesis 1.2.1, this MJCF, 2026-07-23 — see probe_contact*.py)
  * `get_links_net_contact_force()` returns ALL ZEROS -> UNUSABLE (same class
    of silent-zero bug as INC-141 trap #4 `get_vel`). Do not use it.
  * `get_contacts()` WORKS: dict of link_a/link_b/valid_mask/position/normal,
    8 contacts standing (4 spheres x 2 feet). Cost 0.74 ms/call at n_envs=512
    vs 14.1 ms for one scene.step() -> ~0.5% overhead. THIS is the contact
    source.
  * A purely geometric foot-height proxy agreed with real contacts only 70%
    of the time -> rejected.

The model XML, gait reference and quaternion helpers are imported from
`train_v50_walk_tracking` so there is exactly one source of truth for the
simulated body (INC-141 trap #8: a duplicated XML silently broke render checks).
"""
import math
import torch

import train_v50_walk_tracking as V50

DOF_NAMES = V50.DOF_NAMES
N_DOF = len(DOF_NAMES)
FLOOR_Z = -0.92


def _default_cfg():
    return {
        # --- control ---
        "dt_sim": V50.DT_SIM,
        "decimation": V50.DECIMATION,
        "action_scale": V50.ACTION_SCALE,
        "episode_length_s": 20.0,          # was 8 s; walking needs a longer horizon
        "terrain": "none",
        # --- command (target base velocity) ---
        "cmd_vx": [0.15, 0.35],            # resampled uniformly per episode
        "cmd_wz": [-0.2, 0.2],
        "cmd_resample_s": 6.0,
        "cmd_zero_prob": 0.05,             # a few envs are told to stand still
        # --- termination ---
        # Body-ground collision is now detected directly, so the height rule is
        # a backstop rather than the primary fall test. Keeping it at 0.35 (the
        # v1 value) ended 100% of episodes on a squat the policy could still
        # have recovered from; 0.45 leaves that gradient intact and lets
        # `base_height` shape the posture continuously instead.
        "term_upright": 0.55,              # relaxed vs 0.75: recovery is allowed
        "term_height_drop": 0.45,
        # --- observation ---
        "obs_history": 3,
        # --- rendering (None = headless training; renderer supplies a dict) ---
        "camera": None,
        # --- domain randomization ---
        "dr_friction": [0.8, 1.6],
        "dr_mass_scale": [0.9, 1.1],
        "dr_kp_scale": [0.9, 1.1],
        # How many distinct dynamics samples exist across the whole batch.
        # genesis rejects a per-env mass tensor, so envs are split into this many
        # bands. 8 bands over 4096 envs is very little diversity -- a policy can
        # specialise to them, which is one reason the slope run looked robust in
        # its own env and was not (T068). Raise for terrain work.
        "dr_groups": 8,
        "push_interval_s": 5.0,
        "push_vel": 0.35,                  # m/s lateral kick
        # --- reward scales (per second; multiplied by control dt internally,
        #     Genesis/legged_gym convention) ---
        "tracking_sigma": 0.03,            # C6: tight enough that standing pays ~0.1
        "base_height_target": None,        # filled from settled stand height
        "feet_air_time_target": 0.35,      # s; ~half of GAIT_PERIOD
        "reward_scales": {
            "tracking_lin_vel":   2.0,
            "tracking_ang_vel":   0.5,
            "forward_progress":   1.0,
            "feet_air_time":      2.0,     # C1: the anti-freeze term
            "single_foot_contact": 1.0,    # C1: the anti-hop term (2404.19173)
            "pose_prior":         0.3,     # gait reference is a prior, not the goal
            "lin_vel_z":         -2.0,
            "ang_vel_xy":        -0.05,
            "orientation":       -5.0,
            "base_height":      -30.0,
            "action_rate":       -0.01,    # C5
            "dof_vel":           -1e-4,
            "dof_acc":           -2.5e-7,
            "feet_slip":         -0.2,
            "collision":         -2.0,
            "stand_still":       -0.5,
            "termination":     -100.0,
        },
    }


class V50WalkEnv:
    """rsl_rl VecEnv-compatible Genesis environment for the V50 mecha."""

    def __init__(self, num_envs, out_dir, cfg=None, device="cuda", ref_json=None):
        import os
        import genesis as gs

        self.cfg = _default_cfg()
        if cfg:
            rs = self.cfg["reward_scales"].copy()
            rs.update(cfg.pop("reward_scales", {}))
            self.cfg.update(cfg)
            self.cfg["reward_scales"] = rs
        c = self.cfg
        self.device = torch.device(device)
        self.num_envs = num_envs
        self.num_actions = N_DOF

        if ref_json:
            V50.load_reference(ref_json)
        self.gait_period = V50.GAIT_PERIOD
        self.target_vx = V50.TARGET_VX

        self.dt = c["dt_sim"] * c["decimation"]           # control timestep (0.02 s)
        self.max_episode_length = int(c["episode_length_s"] / self.dt)
        self.step_dt = self.dt

        os.makedirs(out_dir, exist_ok=True)
        xml_path = os.path.join(out_dir, "v50_mecha_noact.xml")
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(V50.build_model_xml(c["terrain"]))

        gs.init(backend=gs.gpu, logging_level="warning")
        self.gs = gs
        self.scene = gs.Scene(show_viewer=False,
                              sim_options=gs.options.SimOptions(dt=c["dt_sim"], substeps=2))
        self.robot = self.scene.add_entity(gs.morphs.MJCF(file=xml_path))
        # Optional tracking camera for rollout rendering. It MUST be added before
        # scene.build(), and it lives here rather than in a separate renderer so
        # the video is produced by the exact env that was trained (INC-141 trap
        # #8: a duplicated render-side XML silently diverged from the trainer and
        # made the walk check structurally unable to pass).
        self.camera = None
        if c.get("camera"):
            cc = c["camera"]
            self.camera = self.scene.add_camera(
                res=tuple(cc.get("res", (960, 540))), pos=tuple(cc.get("pos", (3.0, 0.5, 0.6))),
                lookat=tuple(cc.get("lookat", (0.0, 0.0, 0.0))), fov=cc.get("fov", 40),
                GUI=False)
        self.scene.build(n_envs=num_envs)

        self.dof_idx = [self.robot.get_joint(n).dof_idx_local for n in DOF_NAMES]
        self.robot.set_dofs_kp(torch.tensor(V50.KP, device=self.device), self.dof_idx)
        self.robot.set_dofs_kv(torch.tensor(V50.KV, device=self.device), self.dof_idx)

        # link bookkeeping: get_contacts() reports GLOBAL link indices
        names = [l.name for l in self.robot.links]
        self.link_names = names
        ls = self.robot.link_start
        self.foot_local = [names.index("foot_L"), names.index("foot_R")]
        self.foot_global = [i + ls for i in self.foot_local]
        # Link 0 of this MJCF is "world" (the floor plane) and it is the OTHER
        # party of every legitimate foot-ground contact. Including it in the
        # body-collision set terminated every episode after one control step.
        self.body_global = [names.index(n) + ls for n in names
                            if n not in ("world", "foot_L", "foot_R")]

        self.qpos0 = self.robot.get_qpos().clone()
        self.default_dof_pos = torch.zeros(N_DOF, device=self.device)   # MJCF neutral
        for _ in range(300):                              # settle to contact equilibrium
            self.scene.step()
        self.stand_z = float(self.robot.get_qpos()[:, 2].mean())
        if c["base_height_target"] is None:
            c["base_height_target"] = self.stand_z

        self._randomize_dynamics()

        N, dev = num_envs, self.device
        z = lambda *s: torch.zeros(*s, device=dev)
        self.phase = torch.rand(N, device=dev)
        self.episode_length_buf = torch.zeros(N, device=dev, dtype=torch.long)
        self.commands = z(N, 2)                            # [vx, wz]
        self.actions = z(N, N_DOF)
        self.last_actions = z(N, N_DOF)
        self.last_dof_vel = z(N, N_DOF)
        self.lin_vel = z(N, 3)
        self.ang_vel = z(N, 3)
        self.prev_pos = z(N, 3)
        self.prev_quat = z(N, 4)
        self.prev_foot_pos = z(N, 2, 3)
        self.foot_air_time = z(N, 2)
        self.air_prev = z(N, 2)
        self.last_contact = torch.zeros(N, 2, dtype=torch.bool, device=dev)
        self.x0 = z(N)
        self.push_counter = torch.zeros(N, device=dev, dtype=torch.long)
        self.push_interval = max(1, int(c["push_interval_s"] / self.dt))

        self.reward_scales = {k: v * self.dt for k, v in c["reward_scales"].items()}
        self.episode_sums = {k: z(N) for k in self.reward_scales}
        self.extras = {"observations": {}}

        # Episode statistics. rsl_rl only fills its own rewbuffer when its
        # tensorboard logger is active, and tensorboard is deliberately not
        # installed here, so the env owns the telemetry.
        import collections
        self.cur_return = z(N)
        self.cur_length = torch.zeros(N, device=dev, dtype=torch.long)
        self.ret_hist = collections.deque(maxlen=200)
        self.len_hist = collections.deque(maxlen=200)
        self.term_hist = collections.deque(maxlen=200)
        self.metric_hist = collections.deque(maxlen=200)

        self.num_single_obs = 3 + 3 + 3 + 2 + N_DOF * 3 + 2 + 2
        self.num_obs = self.num_single_obs * c["obs_history"]
        self.obs_history = torch.zeros(N, c["obs_history"], self.num_single_obs, device=dev)
        self.num_privileged_obs = None

        self.reset_idx(torch.arange(N, device=dev))
        self._compute_obs()

    # ------------------------------------------------------------------ setup

    def _randomize_dynamics(self, groups=None):
        """Grouped domain randomization of link mass and PD gains.

        genesis 1.2.1 rejects a per-env (N, n_links) mass tensor — `inertial_mass`
        must be at most 1D — but both setters DO accept `envs_idx`. So the envs
        are split into `groups` bands, each given one sampled scale. That is real
        dynamics diversity at build cost only, without fighting the API.

        Geom friction is baked into the MJCF at build time and is not randomized.
        """
        groups = groups if groups is not None else self.cfg.get("dr_groups", 8)
        groups = max(1, min(groups, self.num_envs))
        self.dr_groups = groups
        mlo, mhi = self.cfg["dr_mass_scale"]
        klo, khi = self.cfg.get("dr_kp_scale", [0.9, 1.1])
        base_m = self.robot.get_links_inertial_mass()
        if base_m.dim() > 1:
            base_m = base_m[0]
        kp = torch.tensor(V50.KP, device=self.device)
        kv = torch.tensor(V50.KV, device=self.device)
        chunks = torch.arange(self.num_envs, device=self.device).chunk(groups)
        applied = 0
        for ch in chunks:
            if ch.numel() == 0:
                continue
            ms = float(torch.empty(1).uniform_(mlo, mhi))
            ks = float(torch.empty(1).uniform_(klo, khi))
            try:
                self.robot.set_links_inertial_mass(base_m * ms, envs_idx=ch)
                self.robot.set_dofs_kp(kp * ks, self.dof_idx, envs_idx=ch)
                self.robot.set_dofs_kv(kv * ks, self.dof_idx, envs_idx=ch)
                applied += 1
            except Exception as e:                          # noqa: BLE001
                print(f"[env] domain randomization unavailable ({e!r}); continuing",
                      flush=True)
                self.dr_groups = 0
                return
        print(f"[env] domain randomization: {applied} groups "
              f"(mass x{mlo}-{mhi}, kp/kv x{klo}-{khi})", flush=True)

    # ------------------------------------------------------------- primitives

    def _contacts(self):
        """Per-foot and body contact booleans from get_contacts().

        `get_links_net_contact_force()` is a silent-zero API on this entity —
        probed 2026-07-23, do not substitute it here.
        """
        c = self.robot.get_contacts()
        la, lb, vm = c["link_a"].long(), c["link_b"].long(), c["valid_mask"]
        feet = torch.zeros(self.num_envs, 2, dtype=torch.bool, device=self.device)
        for k, g in enumerate(self.foot_global):
            feet[:, k] = (((la == g) | (lb == g)) & vm).any(dim=1)
        body = torch.zeros(self.num_envs, dtype=torch.bool, device=self.device)
        for g in self.body_global:
            body |= (((la == g) | (lb == g)) & vm).any(dim=1)
        return feet, body

    def _resample_commands(self, idx):
        if idx.numel() == 0:
            return
        c = self.cfg
        n = idx.numel()
        vx = torch.empty(n, device=self.device).uniform_(*c["cmd_vx"])
        wz = torch.empty(n, device=self.device).uniform_(*c["cmd_wz"])
        zero = torch.rand(n, device=self.device) < c["cmd_zero_prob"]
        self.commands[idx, 0] = torch.where(zero, torch.zeros_like(vx), vx)
        self.commands[idx, 1] = torch.where(zero, torch.zeros_like(wz), wz)

    def reset_idx(self, idx):
        if idx.numel() == 0:
            return
        self.robot.set_qpos(self.qpos0[idx], envs_idx=idx, zero_velocity=True)
        self.phase[idx] = torch.rand(idx.numel(), device=self.device)
        ref = V50.gait_reference(self.phase[idx])
        self.robot.set_dofs_position(ref, dofs_idx_local=self.dof_idx, envs_idx=idx,
                                     zero_velocity=True)
        qpos = self.robot.get_qpos()
        self.episode_length_buf[idx] = 0
        self.x0[idx] = V50.FWD_SIGN * qpos[idx, V50.FWD_AXIS]
        self.prev_pos[idx] = qpos[idx, :3]
        self.prev_quat[idx] = qpos[idx, 3:7]
        self.prev_foot_pos[idx] = self.robot.get_links_pos()[idx][:, self.foot_local]
        self.lin_vel[idx] = 0.0
        self.ang_vel[idx] = 0.0
        self.actions[idx] = 0.0
        self.last_actions[idx] = 0.0
        self.last_dof_vel[idx] = 0.0
        self.foot_air_time[idx] = 0.0
        self.last_contact[idx] = True
        self.obs_history[idx] = 0.0
        self._resample_commands(idx)

    def reset(self):
        self.reset_idx(torch.arange(self.num_envs, device=self.device))
        self._compute_obs()
        return self.obs_buf, self.extras

    def get_observations(self):
        return self.obs_buf, self.extras

    # ------------------------------------------------------------------- step

    def step(self, actions):
        c = self.cfg
        self.actions = torch.clip(actions, -5.0, 5.0)
        ref = V50.gait_reference(self.phase)
        target = ref + c["action_scale"] * torch.tanh(self.actions)
        self.robot.control_dofs_position(target, self.dof_idx)
        for _ in range(c["decimation"]):
            self.scene.step()

        self.episode_length_buf += 1
        self.phase = (self.phase + self.dt / self.gait_period) % 1.0

        qpos = self.robot.get_qpos()
        pos, quat = qpos[:, :3], qpos[:, 3:7]
        # INC-141 trap #4: link/base velocity getters are silent zeros on this
        # entity -> finite-difference from get_qpos(), the one verified getter.
        self.lin_vel = (pos - self.prev_pos) / self.dt
        self.ang_vel = V50.quat_angvel(quat, self.prev_quat, self.dt)
        self.prev_pos, self.prev_quat = pos.clone(), quat.clone()

        self.dof_pos = self.robot.get_dofs_position(self.dof_idx)
        self.dof_vel = self.robot.get_dofs_velocity(self.dof_idx)
        self.grav = V50.quat_gravity(quat)
        self.ref = ref
        self.pos = pos

        foot_pos = self.robot.get_links_pos()[:, self.foot_local]
        self.foot_vel = (foot_pos - self.prev_foot_pos) / self.dt
        self.prev_foot_pos = foot_pos.clone()

        # legged_gym order: accumulate -> read at touchdown -> zero on stance.
        # The reward must see the swing duration BEFORE it is cleared.
        self.contacts, self.body_contact = self._contacts()
        self.foot_air_time += self.dt
        self.first_contact = self.contacts & (~self.last_contact)
        self.air_prev = self.foot_air_time.clone()
        self.foot_air_time = torch.where(self.contacts,
                                         torch.zeros_like(self.foot_air_time),
                                         self.foot_air_time)
        self.last_contact = self.contacts

        self._push_robots()
        self._check_termination()
        rew = self._compute_reward()

        self.last_actions = self.actions.clone()
        self.last_dof_vel = self.dof_vel.clone()

        resample = (self.episode_length_buf % int(c["cmd_resample_s"] / self.dt) == 0)
        self._resample_commands(torch.nonzero(resample).squeeze(-1))

        self._track_episode_stats(rew)

        self.extras["time_outs"] = self.time_out_buf
        self.reset_idx(torch.nonzero(self.reset_buf).squeeze(-1))
        self._compute_obs()
        return self.obs_buf, rew, self.reset_buf, self.extras

    def _track_episode_stats(self, rew):
        self.cur_return += rew
        self.cur_length += 1
        done = torch.nonzero(self.reset_buf).squeeze(-1)
        if done.numel():
            self.ret_hist.append(self.cur_return[done].mean().item())
            self.len_hist.append(self.cur_length[done].float().mean().item() * self.dt)
            self.term_hist.append((
                self.terminated[done].float().mean().item(),
                self.term_tilt[done].float().mean().item(),
                self.term_low[done].float().mean().item(),
                self.term_collision[done].float().mean().item(),
            ))
            self.cur_return[done] = 0.0
            self.cur_length[done] = 0
        self.metric_hist.append((
            self._fwd_vel().mean().item(),
            self.upright.mean().item(),
            (self.contacts.float().sum(dim=1) == 1).float().mean().item(),
            self.air_prev[self.first_contact].mean().item() if self.first_contact.any() else 0.0,
        ))

    def stats(self):
        """Windowed training telemetry (means over the last ~200 control steps)."""
        col = lambda d, i, k: (sum(x[i] for x in d) / len(d)) if len(d) else 0.0
        mean = lambda d: (sum(d) / len(d)) if len(d) else 0.0
        m, t = self.metric_hist, self.term_hist
        return {"return": mean(self.ret_hist), "ep_len_s": mean(self.len_hist),
                "fall_rate": col(t, 0, 4), "fall_by_tilt": col(t, 1, 4),
                "fall_by_low": col(t, 2, 4), "fall_by_collision": col(t, 3, 4),
                "vx": col(m, 0, 4), "upright": col(m, 1, 4),
                "single_contact": col(m, 2, 4), "air_time": col(m, 3, 4)}

    def _push_robots(self):
        if self.cfg["push_vel"] <= 0:
            return
        self.push_counter += 1
        hit = self.push_counter % self.push_interval == 0
        idx = torch.nonzero(hit).squeeze(-1)
        if idx.numel() == 0:
            return
        qvel = self.robot.get_dofs_velocity()
        kick = torch.empty(idx.numel(), 2, device=self.device).uniform_(
            -self.cfg["push_vel"], self.cfg["push_vel"])
        qvel[idx, 0:2] += kick
        self.robot.set_dofs_velocity(qvel[idx], envs_idx=idx)

    def _check_termination(self):
        c = self.cfg
        upright = (-self.grav[:, 2]).clamp(0.0, 1.0)
        self.upright = upright
        expect_z = self.stand_z + V50.terrain_dz(self.pos[:, V50.FWD_AXIS], c["terrain"])
        # Kept separate so the supervisor can see WHICH failure mode dominates:
        # tipping over, sinking/diving, or dragging a limb (the crawl hack).
        self.term_tilt = upright < c["term_upright"]
        self.term_low = self.pos[:, 2] < expect_z - c["term_height_drop"]
        self.term_collision = self.body_contact
        fallen = self.term_tilt | self.term_low | self.term_collision
        self.time_out_buf = self.episode_length_buf >= self.max_episode_length
        self.terminated = fallen
        self.reset_buf = fallen | self.time_out_buf

    # ---------------------------------------------------------------- rewards

    def _compute_reward(self):
        rew = torch.zeros(self.num_envs, device=self.device)
        terms = {}
        for name, scale in self.reward_scales.items():
            v = getattr(self, f"_r_{name}")() * scale
            terms[name] = v
            self.episode_sums[name] += v
            rew += v
        self.reward_terms = terms
        return rew

    def _fwd_vel(self):
        return V50.FWD_SIGN * self.lin_vel[:, V50.FWD_AXIS]

    def _moving(self):
        return (self.commands[:, 0].abs() > 0.1).float()

    def _r_tracking_lin_vel(self):
        err = (self.commands[:, 0] - self._fwd_vel()) ** 2
        return torch.exp(-err / self.cfg["tracking_sigma"])

    def _r_tracking_ang_vel(self):
        err = (self.commands[:, 1] - self.ang_vel[:, 2]) ** 2
        return torch.exp(-err / self.cfg["tracking_sigma"])

    def _r_forward_progress(self):
        """Linear, non-vanishing gradient out of v=0. exp() rewards alone are
        flat at standstill, which is what let the freeze basin persist (C4)."""
        cmd = self.commands[:, 0].clamp(min=1e-3)
        return (self._fwd_vel().clamp(min=0.0) / cmd).clamp(max=1.0) * self._moving()

    def _r_feet_air_time(self):
        """legged_gym's anti-freeze term: pay for SWING duration, once per
        touchdown. A standing or marching-in-place policy cannot farm it —
        it is gated on a non-zero velocity command and on real touchdown."""
        t = self.cfg["feet_air_time_target"]
        return ((self.air_prev - t) * self.first_contact.float()).sum(dim=1) * self._moving()

    def _r_single_foot_contact(self):
        """arXiv:2404.19173 reports single-foot contact as the most reliable
        way to get walking rather than hopping. Two feet down = standing,
        zero feet down = flight/hop; exactly one = a stride."""
        n = self.contacts.float().sum(dim=1)
        return (n == 1).float() * self._moving()

    def _r_pose_prior(self):
        """Reference-gait tracking, gated on a walk command. Zero-command envs
        must not be paid for tracking a *moving* gait — their income comes from
        tracking_lin_vel, which is maximal at a standstill when cmd == 0."""
        err = ((self.dof_pos - self.ref) ** 2).mean(dim=1)
        return torch.exp(-8.0 * err) * self._moving()

    def _r_lin_vel_z(self):
        return self.lin_vel[:, 2] ** 2

    def _r_ang_vel_xy(self):
        return (self.ang_vel[:, :2] ** 2).sum(dim=1)

    def _r_orientation(self):
        return (self.grav[:, :2] ** 2).sum(dim=1)

    def _r_base_height(self):
        tgt = self.cfg["base_height_target"] + V50.terrain_dz(
            self.pos[:, V50.FWD_AXIS], self.cfg["terrain"])
        return (self.pos[:, 2] - tgt) ** 2

    def _r_action_rate(self):
        return ((self.actions - self.last_actions) ** 2).sum(dim=1)

    def _r_dof_vel(self):
        return (self.dof_vel ** 2).sum(dim=1)

    def _r_dof_acc(self):
        return (((self.dof_vel - self.last_dof_vel) / self.dt) ** 2).sum(dim=1)

    def _r_feet_slip(self):
        return (self.contacts.float() * (self.foot_vel[:, :, :2] ** 2).sum(dim=2)).sum(dim=1)

    def _r_collision(self):
        return self.body_contact.float()

    def _r_stand_still(self):
        """Zero-command envs are held to the NEUTRAL pose, not to the rolling
        gait reference — measuring them against a walking target would punish
        them for standing, which is exactly what they were told to do."""
        return ((self.dof_pos - self.default_dof_pos).abs().sum(dim=1)) * (1.0 - self._moving())

    def _r_termination(self):
        return self.terminated.float()

    # ----------------------------------------------------------- observations

    def _compute_obs(self):
        two_pi = 2.0 * math.pi
        if not hasattr(self, "dof_pos"):
            self.dof_pos = self.robot.get_dofs_position(self.dof_idx)
            self.dof_vel = self.robot.get_dofs_velocity(self.dof_idx)
            qpos = self.robot.get_qpos()
            self.pos, quat = qpos[:, :3], qpos[:, 3:7]
            self.grav = V50.quat_gravity(quat)
            self.ref = V50.gait_reference(self.phase)
            self.contacts = torch.zeros(self.num_envs, 2, dtype=torch.bool, device=self.device)
        single = torch.cat([
            self.ang_vel * 0.25,                                   # 3
            self.grav,                                             # 3
            self.lin_vel * 2.0,                                    # 3
            self.commands * torch.tensor([2.0, 1.0], device=self.device),   # 2
            self.dof_pos - self.ref,                               # 16
            self.dof_vel * 0.05,                                   # 16
            self.actions,                                          # 16  (C5)
            torch.stack([torch.sin(self.phase * two_pi),
                         torch.cos(self.phase * two_pi)], dim=1),  # 2
            self.contacts.float(),                                 # 2
        ], dim=1)
        self.obs_history = torch.cat(
            [self.obs_history[:, 1:], single.unsqueeze(1)], dim=1)
        self.obs_buf = self.obs_history.reshape(self.num_envs, -1)
        self.extras["observations"] = {}
