# Quality Incident Report: V50 MJX GPU WSL Preflight

- Date: 2026-07-01 JST
- Scope: Independent V50 MJX/PPO/AMP GPU prototype preflight
- Impact: GPU prototype did not start. Existing CPU V50 loops and Becky restore remained running.

## Facts

- Windows `nvidia-smi` detected NVIDIA GeForce RTX 5060 Ti, 16 GB VRAM.
- Windows `.venv` had `mujoco` but not `jax`, `jaxlib`, `brax`, `flax`, or `optax`.
- WSL Ubuntu initially detected the GPU through `nvidia-smi`.
- WSL Python lacked `pip`, `ensurepip`, and `python3.12-venv`.
- `sudo apt-get update && sudo apt-get install python3.12-venv` stalled, likely on sudo or package-manager interaction.
- The agent-created apt process was stopped.
- User-space `uv` was installed under `/home/yasu/.local/bin`.
- `uv venv` started and `jax[cuda12]`, `mujoco`, `brax`, `flax`, and `optax` downloads began.
- During or after package installation, WSL Ubuntu entered a startup failure state:
  - `getpwnam(yasu) failed 5`
  - `getpwuid(1000) failed 5`
  - `WSL_E_USER_NOT_FOUND`
  - `E_FAIL`

## 5 Whys

1. Why did the MJX GPU prototype fail?
   - Because WSL could not reliably start a Python/JAX GPU environment.
2. Why could WSL not create the environment normally?
   - The distro lacked pip/venv/ensurepip, and sudo package installation did not complete.
3. Why did the fallback user-space install fail?
   - `uv` could create the venv and start downloads, but WSL later failed to resolve local users.
4. Why did WSL user resolution fail?
   - Unknown from current evidence; likely WSL distro/service filesystem or account metadata access failure after package-manager/user-space environment activity.
5. Why was this not caught earlier?
   - The preflight checked GPU visibility first but did not verify WSL package-manager health, pip/venv availability, and user database readability before installation.

## FMEA

| Failure Mode | Effect | Detection | Countermeasure |
|---|---|---|---|
| Missing WSL pip/venv | Cannot create isolated Python env | `python3 -m pip`, `python3 -m venv` | Check before install; avoid sudo unless interactive path is known |
| sudo apt stalls | Long-running blocked process | no output/progress for timeout window | Kill only agent-created apt process; prefer user-space toolchain |
| WSL user database failure | Distro cannot launch commands | `getpwnam`, `WSL_E_USER_NOT_FOUND` | Stop GPU prototype; perform WSL health recovery before retry |
| Prototype contaminates main V50 loop | Loss of ongoing work | Process/status checks | Keep MJX branch separate; do not replace CPU loop |

## Countermeasures

- Before retrying MJX/PPO/AMP GPU, run a WSL health gate:
  - `wsl -l -v`
  - `wsl -- bash -lc "id; getent passwd yasu; getent passwd 1000; nvidia-smi"`
  - `wsl -- bash -lc "python3 --version; python3 -m pip --version || true; python3 -m venv --help || true"`
- If WSL user resolution fails, do not run any more package installation.
- If WSL recovers but lacks pip/venv, choose one of:
  - user-approved apt repair/install,
  - user-space `uv` with a fresh directory,
  - Docker GPU container route if Docker Desktop GPU support is healthy.
- Keep V50 CPU elite loop and Telegram gates as the active production path until MJX GPU passes smoke tests.

## Current Safe State

- CPU guided elite branch is running separately.
- Becky attachment restore is running separately.
- No source V50 baseline video or Becky source was modified by the MJX preflight.
