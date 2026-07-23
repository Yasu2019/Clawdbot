# -*- coding: utf-8 -*-
"""Baseline sanity check: can the body survive on the reference gait ALONE?

This is the test that should have been run before any reward tuning. If the
open-loop reference gait (zero policy action, PD tracking the retargeted 100STYLE
walk) collapses on its own, then no reward function can produce a walk — the
blocker is the body/gains/reference, not RL. Every "walks then falls at 4-7 s"
escalation since 2026-07-20 is consistent with that hypothesis being untested.

Reports, per control step: base height, upright, forward travel, per-foot contact.

  python check_reference_gait.py --seconds 20
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import torch

import train_v50_walk_tracking as V50


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=20.0)
    ap.add_argument("--n-envs", type=int, default=16)
    ap.add_argument("--ref-json", default=None)
    ap.add_argument("--terrain", default="none")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out = args.out or os.path.join(os.environ.get("TEMP", "."), "ref_gait_check")
    os.makedirs(out, exist_ok=True)
    if args.ref_json:
        V50.load_reference(args.ref_json)

    import genesis as gs
    xml = os.path.join(out, "ref_check.xml")
    open(xml, "w", encoding="utf-8").write(V50.build_model_xml(args.terrain))
    gs.init(backend=gs.gpu, logging_level="warning")
    scene = gs.Scene(show_viewer=False,
                     sim_options=gs.options.SimOptions(dt=V50.DT_SIM, substeps=2))
    robot = scene.add_entity(gs.morphs.MJCF(file=xml))
    scene.build(n_envs=args.n_envs)

    names = [l.name for l in robot.links]
    foot = [names.index("foot_L"), names.index("foot_R")]
    foot_g = [i + robot.link_start for i in foot]
    body_g = [names.index(n) + robot.link_start for n in names
              if n not in ("world", "foot_L", "foot_R")]
    dof = [robot.get_joint(n).dof_idx_local for n in V50.DOF_NAMES]
    robot.set_dofs_kp(torch.tensor(V50.KP, device="cuda"), dof)
    robot.set_dofs_kv(torch.tensor(V50.KV, device="cuda"), dof)
    for _ in range(300):
        scene.step()
    stand_z = float(robot.get_qpos()[:, 2].mean())
    print(f"stand_z(settled) = {stand_z:.4f}  period={V50.GAIT_PERIOD}s "
          f"target_vx={V50.TARGET_VX}", flush=True)

    dt = V50.DT_SIM * V50.DECIMATION
    steps = int(args.seconds / dt)
    phase = torch.zeros(args.n_envs, device="cuda")
    robot.set_dofs_position(V50.gait_reference(phase), dofs_idx_local=dof,
                            zero_velocity=True)
    y0 = (V50.FWD_SIGN * robot.get_qpos()[:, V50.FWD_AXIS]).clone()

    log, first_fall = [], None
    for k in range(steps):
        robot.control_dofs_position(V50.gait_reference(phase), dof)
        for _ in range(V50.DECIMATION):
            scene.step()
        phase = (phase + dt / V50.GAIT_PERIOD) % 1.0
        qpos = robot.get_qpos()
        grav = V50.quat_gravity(qpos[:, 3:7])
        upright = (-grav[:, 2]).clamp(0, 1)
        c = robot.get_contacts()
        la, lb, vm = c["link_a"].long(), c["link_b"].long(), c["valid_mask"]
        feet = [(((la == g) | (lb == g)) & vm).any(dim=1).float().mean().item()
                for g in foot_g]
        body = torch.zeros(args.n_envs, dtype=torch.bool, device="cuda")
        for g in body_g:
            body |= (((la == g) | (lb == g)) & vm).any(dim=1)
        z = qpos[:, 2].mean().item()
        up = upright.mean().item()
        travel = (V50.FWD_SIGN * qpos[:, V50.FWD_AXIS] - y0).mean().item()
        bad = (up < 0.55) or (z < stand_z - 0.45) or bool(body.any())
        if bad and first_fall is None:
            first_fall = round(k * dt, 2)
            print(f"  !! failed at t={first_fall}s  z={z:.3f} up={up:.3f} "
                  f"body_contact={bool(body.any())}", flush=True)
        if k % 25 == 0:
            print(f"  t={k*dt:5.2f}s z={z:6.3f} up={up:5.3f} travel={travel:6.3f} "
                  f"contactL/R={feet[0]:.2f}/{feet[1]:.2f}", flush=True)
        log.append({"t": round(k * dt, 3), "z": round(z, 4), "upright": round(up, 4),
                    "travel": round(travel, 4),
                    "contact_L": round(feet[0], 3), "contact_R": round(feet[1], 3)})

    final = log[-1]
    res = {"schema": "clawstack.reference_gait_check.v1",
           "stand_z": round(stand_z, 4), "seconds": args.seconds,
           "gait_period": V50.GAIT_PERIOD, "target_vx": V50.TARGET_VX,
           "survived": first_fall is None, "first_fail_sec": first_fall,
           "final_travel_m": final["travel"], "final_z": final["z"],
           "final_upright": final["upright"],
           "mean_contact_L": round(sum(x["contact_L"] for x in log) / len(log), 3),
           "mean_contact_R": round(sum(x["contact_R"] for x in log) / len(log), 3),
           "verdict": ("reference gait is a viable base: RL only has to correct it"
                       if first_fall is None else
                       "REFERENCE GAIT ITSELF FAILS: fix body/gains/reference "
                       "before tuning any reward")}
    with open(os.path.join(out, "reference_gait_check.json"), "w", encoding="utf-8") as f:
        json.dump({"result": res, "trace": log}, f, indent=2)
    print("RESULT:", json.dumps(res, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
