# Sanitized solver restart qualification update — 2026-11-02 JST

A current integrity-only recheck found all four retained finite qualification records and their native-restart proof files matching their expected SHA-256 values. The current OpenFOAM, CalculiX, Elmer and OpenRadioss binaries also match their recorded qualified binary hashes. No solver was run during this integrity recheck.

The retained evidence covers narrowly bounded examples: OpenFOAM laminar cavity recovery; CalculiX unit-cube thermal expansion with completed-step restart; Elmer finite transient heat restart using one MPI rank and one thread; and an OpenRadioss finite slice graceful-stop/native-resume case. These records establish restart behavior only for those exact test inputs, versions and layouts. They do not validate arbitrary production models, coupled analyses, high-memory cases, or an unrelated active worker.

Keep production dispatch gated on case-specific inputs, binary/version and parallel-layout compatibility, verified solver-native checkpoint/resume on an isolated copy, RAM budget and separate production authorization. This note contains no host names, addresses, accounts, process IDs, internal paths, raw logs or credentials. Source: reviewed note INC-K1MMENT-K1-SOLVER-QUALIFICATION-PROOF-REFRESH-20261102T1057JST.md.
