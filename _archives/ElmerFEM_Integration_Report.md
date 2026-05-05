# ElmerFEM Integration Report: Challenges & Solutions

## 1. Project Objective

**Goal:** Integrate ElmerFEM (v9.0) into the Debian 12 (Bookworm) based Docker environment to enable thermal stress and warpage analysis for injection molding simulation.

## 2. Executive Summary

The integration faced significant compatibility hurdles because ElmerFEM packages are not natively available for Debian Bookworm. We successfully implemented a "Direct Extraction" strategy, manually pulling Ubuntu 22.04 LTS packages and resolving a deep tree of missing dependencies. The final system is now fully operational.

## 3. Challenge Log & Resolutions

### Challenge 1: Incompatible Repositories

- **Issue:** Adding Ubuntu PPAs (`ppa:elmer-csc-ubuntu`) to Debian Bookworm caused catastrophic `apt` dependency errors due to mismatched `libc6` and `libstdc++` versions.
- **Resolution:** Abandoned `apt-get install`. Adopted a **Direct Extraction Strategy**: downloading specific `.deb` files and extracting them using `dpkg -x` to bypass package manager constraints.

### Challenge 2: The "Dependency Hell"

ElmerSolver (MPI version) required numerous shared libraries not present in Debian. Each run revealed a new missing library.

| Missing Library | Required By | Resolution (Package Source) |
| :--- | :--- | :--- |
| `libmumps_common-5.4.so` | ElmerSolver | **Download**: `libmumps-5.4` (Ubuntu 22.04) |
| `libparmetis.so.4.0` | ElmerSolver | **Download**: `libparmetis4.0` (Ubuntu 22.04) |
| `libHYPRE-2.22.1.so` | ElmerSolver | **Download**: `libhypre-2.22.1` (Ubuntu 22.04) |
| `libscalapack-openmpi.so.2.1` | ElmerSolver | **Download**: `libscalapack-openmpi2.1` (Ubuntu 22.04) |
| `libsuperlu_dist.so.7` | ElmerSolver | **Download**: `libsuperlu-dist7` (Ubuntu 22.04) |
| `libptscotchparmetis-6.1.so` | ElmerSolver | **Download**: `libptscotch-6.1` (Ubuntu 22.04) |
| `libCombBLAS.so.1.16.0` | ElmerSolver | **Download**: `libcombblas1.16.0` (Ubuntu 22.04) |

### Challenge 3: Docker Build Failures (Copy Command)

- **Issue:** A standard `cp -r` command failed during the build because different Ubuntu packages extracted libraries to different paths (some to `/usr/lib`, others to `/usr/lib/x86_64-linux-gnu`).
- **Resolution:** Implemented a robust `find` command in the `Dockerfile` to locate all `.so` files regardless of their extraction path and copy them to a unified directory (`/usr/lib/elmersolver`).

  ```bash
  find /tmp/extracted/usr/lib -name "*.so*" -exec cp -P {} /usr/lib/elmersolver/ \;
  ```

### Challenge 4: Build Cache Invalidation

- **Issue:** Repeated "pip install" executions wasted time.
- **Cause:** Repeated build failures and cancellations caused the Docker daemon to invalidate the cache for safety.
- **Resolution:** The final successful build has generated a valid cache layer. Future builds will skip the heavy Python installation steps.

## 4. Final System Status

- **OS:** Debian 12 (Bookworm)
- **ElmerFEM:** Version 9.0 (Rev: 2026-02-12) - Fully Functional
- **Portability:**
  - `docker-compose.yml` updated to use relative paths (`./data/...`).
  - `Dockerfile` contains all dependency resolution logic (no manual steps required on new machines).

## 5. How to Reproduce (On a new machine)

1. Install Docker Desktop.
2. Clone/Copy the `Clawdbot_Docker_20260125` folder.
3. Run `docker compose up -d --build`.
4. Verify with `docker exec clawdbot-gateway ElmerSolver -v`.
