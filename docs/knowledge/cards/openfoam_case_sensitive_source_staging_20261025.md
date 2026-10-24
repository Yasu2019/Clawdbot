# OpenFOAM 3.0.0 source staging must preserve case-distinct paths

The OpenFOAM Foundation 3.0.0 source archive contains case-distinct `Scalar.H` and `scalar.H` include links. Extracting it first onto a case-insensitive Windows filesystem can silently lose case-distinct files or symlinks; copying that incomplete tree to Linux does not restore them. In the observed build attempt, the Windows-staged tree lacked `scalar.H`, and the first core build stopped with a missing-header error. Direct extraction of the original archive into Linux ext4 preserved both links and exposed additional case-distinct entries.

For Linux OpenFOAM builds, extract the verified original archive directly into a case-sensitive filesystem and verify the archive-derived file/link manifest and exact-case links before building. A matching hash between an incomplete staging tree and its later copy proves only that the copy matches that tree. The separate OpenFOAM 14 API mismatch remains a different compatibility issue. This observation does not validate the custom resin solver or its physics.
## Follow-up: isolate the missing Flex development header

The case-safe OpenFOAM 3.0.0 build then reached `surfMesh` and stopped with `FlexLexer.h` missing (exit code 2). The `flex` 2.6.4 executable was present, while its `libfl-dev` development package was absent. Installing `libfl-dev` 2.6.4-8build2 and `libfl2` inside the isolated OpenFOAM WSL distro provided the header. A separate single-job, lower-priority incremental build was active at 00:37 JST on 2026-10-25; its result is still pending. This does not establish that the custom resin solver compiles or that molding physics are validated.

## 2026-10-25 00:53 JST follow-up

The isolated OpenFOAM 3.0.0 stock build on G3 remained active in a serial finiteVolume compile; the log tail showed no fatal error. The missing Flex development header repair is therefore progressing, but no full-build exit code is available yet. Focused local source/reference regressions passed 4/4; these do not prove the target C++ build or solver runtime. The custom solver and resin physics remain unverified.

## 2026-10-25 01:05 JST build-retry follow-up

The first complete stock-build attempt reached `oscillatingFixedValue` and exited 2 because four legacy scalar accessors return `autoPtr<DataEntry<scalar>>` members. This was confirmed in the official 3.0.0 source archive (publisher MD5 matched) and no in-tree callers were found. The original archive and failed build tree were preserved. A fresh case-sensitive ext4 extraction removes only those invalid accessors; a corrected serial `nice 10` build retry is active in OpenMPI Pstream compilation. Local reference tests passed 4/4 but do not verify this C++ build or solver runtime. Resin FEM remains undispatched.

## 2026-10-25 01:17 JST build and regression follow-up

Direct SSH to G3 and WSL `OpenFOAM14-G3` confirmed the foreground serial `Allwmake libso` retry active at 01:17 JST, compiling `globalPoints.C`; WSL reported 7.6 GiB total / 7.1 GiB available. No exit marker was present. Six focused local Python/reference suites passed 44/44, covering void mechanism, population transport, nucleation, bubble dynamics, checkpoint audit, and Cross-WLF source bounds. These are not OpenFOAM 3.0.0 C++ build, solver runtime, dynamic-mesh conservation, or physical-accuracy evidence. No resin FEM was dispatched and no native restart point has been verified.

The follow-up restart/coupling contract batch (`test_run_void_bidirectional_coupling`, `test_validate_void_full_coupling_gate`, `test_vivobook_checkpoint_generations`, `test_airtrap_compressible`) passed 21 with 1 skipped. Combined focused Python/reference contract evidence is 65 passed / 1 skipped. The coupling tests use fake adapters with `actual_solve=false`; no target solver runtime, physical comparison, or FEM checkpoint was demonstrated.

A source-level caller audit also searched the isolated G3 custom solver-port tree for the `amplitude` and `frequency` accessors removed by the OF3 compatibility patch; neither identifier was used in the port. This complements the upstream stock source/application search but does not substitute for compiling the patched core and the port.

Additional focused phenomenon regressions at 01:26 JST passed 49/49 across weld-front collision, air-trap connectivity, sink/shrinkage displacement, weld-line KPI, and void history/report contracts. Combined selected local Python/reference/harness evidence: 114 passed / 1 skipped. These are not solver runtime or physical validation.

Resource check at 01:28-01:29 JST: G3 Windows 4 physical/4 logical CPUs, 15.75 GiB OS-visible / 8.79 GiB available; two-second total CPU samples 26.0%, 25.8%. Separate WSL guest 7.6 GiB total / 7.1 GiB available / 0 swap. Serial stock build remains active. Host and guest memory are reported separately; no product FEM was launched.
