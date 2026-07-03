# -*- coding: utf-8 -*-
"""Genesis GPU smoke test for V50 mecha MJCF (execution queue item 4).

Success criteria (decision doc: fable5_mecha_multirobot_scaleup_decision_20260703.md):
  1. genesis initializes with GPU backend on native Windows (RTX 5060 Ti / sm_120)
  2. V50 MJCF loads as an entity
  3. batched scene builds (n_envs) and steps N frames without error
  4. report device + FPS to JSON

This is a SIM smoke, with random PD position targets on the 12 actuated DOFs
(a stand-in for policy actions). Full PPO training is Stage A, not this smoke.
"""
import sys, json, time, traceback

MJCF = r"D:\Clawdbot_Docker_20260125\projects\AtsugiMechaCity\rl_integration\artifacts\v50_mecha.xml"
OUT = r"C:\v50_work\genesis_smoke_report.json"
N_ENVS = 64
N_STEPS = 300

report = {"schema": "clawstack.genesis_v50_smoke.v1", "mjcf": MJCF,
          "n_envs": N_ENVS, "n_steps": N_STEPS, "stages": {}, "ok": False}

def stage(name, fn):
    t0 = time.time()
    try:
        result = fn()
        report["stages"][name] = {"ok": True, "sec": round(time.time()-t0, 2)}
        print(f"[OK] {name} ({report['stages'][name]['sec']}s)")
        return result
    except Exception as e:
        report["stages"][name] = {"ok": False, "sec": round(time.time()-t0, 2),
                                  "error": f"{type(e).__name__}: {e}",
                                  "trace": traceback.format_exc()[-2000:]}
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        sys.exit(2)

def s_torch():
    import torch
    info = {"torch": torch.__version__, "cuda_available": torch.cuda.is_available()}
    if torch.cuda.is_available():
        info["device"] = torch.cuda.get_device_name(0)
        info["capability"] = ".".join(map(str, torch.cuda.get_device_capability(0)))
    report["torch"] = info
    assert torch.cuda.is_available(), "torch CUDA not available"
    return info

def s_import():
    import genesis as gs
    report["genesis_version"] = getattr(gs, "__version__", "unknown")
    return gs

def s_init():
    gs.init(backend=gs.gpu)
    return True

def s_scene():
    scene = gs.Scene(
        show_viewer=False,
        sim_options=gs.options.SimOptions(dt=0.002, substeps=2),
    )
    scene.add_entity(gs.morphs.Plane())
    robot = scene.add_entity(gs.morphs.MJCF(file=MJCF))
    return scene, robot

def s_build():
    scene.build(n_envs=N_ENVS)
    return True

def s_dofs():
    import torch
    names = ["hip_L","knee_L","ankle_L","hip_R","knee_R","ankle_R",
             "shoulder_L","elbow_L","wrist_L","shoulder_R","elbow_R","wrist_R"]
    idx = []
    for n in names:
        try:
            j = robot.get_joint(n)
            idx.append(j.dof_idx_local if not isinstance(j.dof_idx_local, list) else j.dof_idx_local[0])
        except Exception:
            pass
    report["controlled_dofs"] = len(idx)
    return idx

def s_steps():
    import torch
    t0 = time.time()
    for i in range(N_STEPS):
        if dof_idx:
            targets = (torch.rand(N_ENVS, len(dof_idx), device="cuda") - 0.5) * 0.4
            try:
                robot.control_dofs_position(targets, dof_idx)
            except Exception:
                pass  # control API mismatch must not kill the sim smoke
        scene.step()
    dt = time.time() - t0
    fps = N_STEPS * N_ENVS / dt
    report["steps_sec"] = round(dt, 2)
    report["env_steps_per_sec"] = round(fps)
    print(f"stepped {N_STEPS} x {N_ENVS} envs in {dt:.2f}s -> {fps:,.0f} env-steps/s")
    return True

stage("torch_cuda", s_torch)
gs = stage("import_genesis", s_import)
stage("gs_init_gpu", s_init)
scene, robot = stage("scene_and_mjcf_load", s_scene)
stage("build_batched", s_build)
dof_idx = stage("resolve_dofs", s_dofs)
stage("sim_steps", s_steps)

report["ok"] = True
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print("SMOKE_OK ->", OUT)
