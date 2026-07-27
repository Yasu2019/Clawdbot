# INC-175: False commercial-quality approval of the Tokimeki Unity screen

## Triage

Classification: customer complaint and internal quality escape.

### Confirmed facts

- The user reviewed the delivered Unity screen and rejected it as 100%
  impossible to commercialize.
- The final image visibly contains a crude low-poly character, weak shoulder,
  elbow, wrist and hand presentation, an arms-out idle pose, primitive mouth,
  flat blue background, white floor, generic rectangular UI, and a Development
  Build watermark.
- Source code creates the lip-sync mouth with
  `GameObject.CreatePrimitive(PrimitiveType.Sphere)`.
- Source code creates panels and buttons from plain UGUI `Image` objects and
  solid colors.
- The Player was built with `BuildOptions.Development`.
- Prior gates proved execution, not product desirability or art quality.

### Missing information

- Approved target art direction and exact reference screens.
- Target platform, resolution, age rating, and performance budget.
- Whether the current character design should be rebuilt or replaced.
- Required facial-expression and voice/lip-sync fidelity.

### Immediate containment

1. Retract all commercial-quality approval language.
2. Preserve the build only as a functional diagnostic prototype.
3. Invalidate success case S026 for product-quality reuse.
4. Do not send or present the current visual as a sales/demo build.
5. Do not resume corrective implementation until the user confirms the plan.

## 5 Whys

1. Why was an unusable screen approved? The gate returned PASS.
2. Why did the gate pass? It checked compile status, callbacks, PNG size,
   interaction count, and mouth amplitude.
3. Why were those treated as commercial criteria? Functional readiness and
   presentation readiness were not separated.
4. Why was presentation readiness not measured? There was no approved reference
   set, weighted art/UI/animation rubric, real-motion review, or human acceptance
   gate.
5. Why was the claim still made? The agent overrode the explicit limitations
   visible in the asset and used optimistic language instead of failing closed.

## Fishbone / FTA

- Character art: primitive proportions, weak silhouette, crude face/hair/hands.
- Rig/animation: arms-out pose, poor joint appearance, no expressive acting.
- Facial system: no BlendShapes/Jaw; added sphere mouth is not a valid product
  solution.
- Environment: no authored background, lighting composition, props, or depth.
- UI/UX: debug rectangles, weak hierarchy and spacing, no authored components,
  transitions, feedback, or cohesive visual identity.
- Release hygiene: Development Build watermark remained.
- Measurement: numeric smoke metrics had no correlation with perceived quality.
- Governance: the user's acceptance was not a mandatory promotion gate.

Top event: `non-commercial prototype labelled commercial`.

- OR branch A: visual defects not measured.
- OR branch B: functional PASS promoted directly to commercial.
- OR branch C: known facial limitations accepted without an art-quality veto.
- OR branch D: no independent/user acceptance before reporting completion.

## FMEA

| Failure mode | Effect | Severity | Existing detection | Required control |
|---|---:|---:|---|---|
| Prototype art presented as final | Product rejection | 10 | None | Reference-based art review |
| Primitive mouth fallback | Face becomes uncanny | 10 | Amplitude only | BlendShape/Jaw rebuild gate |
| Debug UI presented as product UI | Low trust/usability | 9 | Click callback | Visual system and UX rubric |
| Static screenshot used as motion proof | Animation defects hidden | 9 | PNG exists | Real-time 15-30 s capture |
| Development watermark | Release appears unfinished | 7 | None | Non-development build gate |
| Agent self-approval | False promotion | 10 | Same evaluator | User acceptance required |

## Corrective plan proposed for confirmation

### Phase 0: Quality contract

- Obtain 3-5 approved reference screens and define a non-infringing visual
  direction.
- Define weighted gates for character 30%, facial/acting 20%, UI/UX 20%,
  environment/lighting 15%, animation/camera 10%, release hygiene 5%.
- Any category below 70/100 is a hard fail; overall commercial candidate requires
  at least 85/100 and explicit user acceptance.

### Phase 1: Character veto gate

- Stop UI polish until silhouette, face, hair, hands, clothing, topology,
  materials, skinning, neutral pose, and close-up render pass.
- Remove the sphere-mouth system. Add proper facial BlendShapes/visemes or use a
  character asset that includes them.

### Phase 2: Art-directed vertical slice

- Build one polished conversation screen only: authored background, lighting,
  camera, character pose/expression, dialogue box, nameplate, one choice, hover
  and selection feedback.
- Review one still and one real-time motion capture before expanding features.

### Phase 3: Systems expansion

- Only after approval, integrate schedule screen, stats, transitions, save/load,
  sound, voice, accessibility, and performance.

### Phase 4: Promotion gate

- Non-development Windows build.
- 15-30 second real gameplay recording with dialogue, expression, lip sync,
  camera and schedule interaction.
- Side-by-side rubric scoring against approved references.
- Explicit user acceptance is mandatory before using `commercial quality`.

## Verification and rollback

Pass requires the artifacts and scores above; compile/test success alone can
never promote presentation quality. The current build remains recoverable at
`D:\Local_AI_GameDev_Master\_unity_project_backups\02_UnityProject_20260727_ui_lipsync`
and is labelled diagnostic prototype only.

## Scope limits

This report proves the previous approval was invalid. It does not yet select a
new art style, asset source, or reconstruction method. Those decisions require
the user's confirmation of the corrective plan.

## Provenance

- User complaint: 2026-07-27 JST
- Rejected image:
  `logs/tokimeki_commercial_render_v6_20260727.png`
- Source:
  `D:\Local_AI_GameDev_Master\02_UnityProject\Assets\Editor\TokimekiCommercialPresentationBuilder.cs`
- Beads: `Clawdbot_Docker_20260125-7xe6`
