# CAD projection reconstruction — sanitized follow-up

Incident: INC-380D-INTERFERENCE-20261107-01. Observed 2026-11-08T08:46:54.143224+09:00, direct source drawings and owned CAD build/reimport/browser checks.

- A DXF annotation layer can also contain genuine model edges. Model ROI selection and independent dimension checks are required; blanket layer exclusion and blanket polygon union both fail.
- A partial orthographic projection can clip a valid body to the wrong length. A valid BRep is not evidence of drawing conformity.
- A geometry vector operation mutated an extrusion normal. Exit0 coexisted with zero-volume outputs. Explicit expected-count, positive-volume and single-solid gates detected the failure. Separate vectors fixed it; all expected review exports and reimports then passed.
- Review models retain unresolved machining details and placement, and must remain separate from released manufacturing/FEM geometry. Reconstruction evidence is not a full-stroke or forming acceptance.

FMEA: wrong projection/annotation/empty-solid failure modes; residual detail risks open; S/O/D unassessed. FTA: independent OR branches for extraction, projection, extrusion, and omitted features. QC: source identity -> ROI/dimension gate -> valid positive solid -> independent reimport -> engineering qualification. Control Plan: repeat per revision, preserve failed evidence and hold release until local features/placement meet actual source requirements. Validation passed for review export/reimport/display, not engineering release.
