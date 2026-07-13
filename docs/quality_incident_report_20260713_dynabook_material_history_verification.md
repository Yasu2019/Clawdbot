# Dynabook Moldflow material history verification incident

- Date: 2026-07-13 JST
- Scope: read-only verification of Dynabook Moldflow material DB import history
- Impact: import completion count and DB contents could not be independently verified from K10

## Confirmed facts

- Dynabook is registered at `100.98.133.40:5683`; the latest node status records `/healthz` HTTP 200.
- `scripts/import_moldflow_materials.py` scans Moldflow 2010 `data/udb` and `data/dat`, upserts `moldflow_material_files` into SQLite, and optionally syncs Turso.
- No `data/workspace/moldflow_materials.db` exists on K10.
- No `scan_count`, `sqlite_ok`, or `turso=ok` execution record for the reported import was found in the scoped K10 logs.
- A read-only Dynabook job submitted on 2026-07-13 was disconnected before returning a result.

## RCA

### 5 Whys

1. Why was the imported row count not confirmed? The Dynabook query returned no result.
2. Why did it return no result? The worker closed the POST connection unexpectedly.
3. Why was there no alternate proof? The importer prints results to stdout but does not persist a status artifact by default.
4. Why could K10 not inspect a replicated DB? The local K10 SQLite file does not exist; Turso synchronization is optional.
5. Why is history incomplete? Import execution, DB destination, and verification evidence are not bound into one durable manifest.

### FTA / Fishbone summary

- Connectivity: health endpoint and job execution path have different reliability.
- Evidence: no durable import manifest or captured stdout.
- Storage: possible Dynabook-only SQLite or Turso-only state.
- Tooling: the K10 dispatcher also lacked its `httpx` runtime dependency.
- Search: broad repository and ByteRover queries exceeded bounded execution/context limits.

## Countermeasures

1. Treat the import as user-reported, not independently verified, until a DB aggregate or import manifest is obtained.
2. On Dynabook, record `scan_count`, row count, unique hashes, first/last import time, DB path, and Turso status in a JSON status artifact.
3. Copy only that small status artifact to K10 or expose it through a read-only endpoint.
4. Keep verification queries scoped to named paths; do not recursively scan the entire repository.
5. Verify the satellite job runtime dependencies before dispatch; do not install or modify them without a separate approved fix.

## Web knowledge decision

No web search was used. The incident concerns local paths, local worker behavior, and project-specific logging; external sources would not establish whether this specific import completed.

## Current disposition

`UNVERIFIED`: implementation exists and Dynabook registration/health are confirmed, but imported row count, duplicates, and final DB destination remain unverified.
