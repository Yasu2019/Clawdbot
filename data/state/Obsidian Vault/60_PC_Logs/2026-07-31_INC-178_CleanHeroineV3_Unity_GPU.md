# INC-178 CleanHeroineV3 Unity GPU motion validation

## Goal and scope

Build and visually validate the isolated CleanHeroineV3 assets in a real Windows
Unity Player using the local RTX 5060 Ti. Legacy v23 assets, Build Settings,
manifest, and disabled scheduled tasks were protected.

## Observed facts

- Retry 17: Player build PASS, warnings 0, errors 0.
- Retry 17 runtime: Direct3D11 on RTX 5060 Ti; three 720x900 PNGs created.
- Mid-frame visibly showed both arms rotating outward.
- Old metric: hand translation 0.0015009 m, final status FAIL.
- Retry 18: hand maximum angular delta 24.3901 degrees, status PASS.
- GPU samples peaked at 5% utilization and 108 MiB VRAM.

## 5 Why / FTA

1. FAIL occurred because hand translation was below 0.01 m.
2. Translation was small because motion primarily changes joint rotation.
3. Rotation was missed because only position was measured.
4. Endpoint sampling hid motion because the clip returns near its initial pose.
5. Review disagreed because the metric did not match the visual motion category.

Fault tree: false FAIL = translation-only probe OR endpoint-only probe.

## Fishbone and FMEA

- Method: endpoint displacement used for a cyclic clip.
- Measurement: no angular metric.
- Machine: GPU and Direct3D11 operated normally.
- Model: rig and controller loaded; no missing probe bones.

| Failure mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| Rotation motion marked static | False rejection | 3 | 4 | 3 | 36 | Sample maximum bone angle at 3 times |
| Final pose hides motion | Retry waste | 3 | 3 | 3 | 27 | Include midpoint and screenshots |

Residual RPN is 3 after angular sampling (S3/O1/D1).

## Procedure, QC, and rollback

1. Build the validation scene as a Windows64 Player.
2. Launch without `-batchmode` or `-nographics`.
3. Capture normalized times 0.03, 0.50, and 0.96.
4. Record GPU/API, position, and maximum angular deltas.
5. Pass when hand rotation exceeds 10 degrees and a secondary probe changes.
6. Inspect all frames for framing, separated topology, shading, shadow, and pose.

Expected output is the three PNGs plus the retry18 JSON. Restore the two scripts
from backup commit `d046f0936` to roll back. This proves sampled motion and GPU
rendering, not photorealism or production-game readiness. Web search was not
needed because local logs, images, and transform measurements isolated the cause.

