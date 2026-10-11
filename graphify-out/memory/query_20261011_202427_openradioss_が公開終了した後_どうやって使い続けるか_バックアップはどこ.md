---
type: "query"
date: "2026-10-11T20:24:27.321219+00:00"
question: "OpenRadioss が公開終了した後、どうやって使い続けるか？バックアップはどこ？"
contributor: "graphify"
---

# Q: OpenRadioss が公開終了した後、どうやって使い続けるか？バックアップはどこ？

## Answer

Siemens が 2026-10-01 に OpenRadioss を閉鎖。手元の Docker イメージ clawstack-unified-openradioss:latest（2026-06-15 版）は動く。控え: H:\clawstack_archive\openradioss_backup_20261011（実行ファイル tar.gz・docker イメージ・OpenCourant ミラー）、GitHub 非公開 Yasu2019/openradioss-backup と Yasu2019/OpenCourant-mirror、Google Drive gdrive:OpenRadioss_backup_20261011、Turso knowledge_backups、Obsidian と Beads と ByteRover に手順。復元は image の分割 tar を結合して docker load、またはオフライン Dockerfile で build。後継ソースは OpenCourant（AGPL v3）。