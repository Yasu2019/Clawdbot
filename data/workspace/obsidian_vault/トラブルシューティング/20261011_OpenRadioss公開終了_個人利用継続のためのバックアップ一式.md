---
created: 2026-10-11 23:15
tags: [openradioss, backup, opencourant, inc188]
source: claude-code session (INC-188)
---

# OpenRadioss 公開終了（2026-10-01）と、個人利用継続のためのバックアップ一式

## 何が起きたか

Siemens が 2026-10-01 に OpenRadioss の公開を終了し、公式 GitHub（github.com/OpenRadioss/OpenRadioss）とリリースの
ダウンロードを削除した（いまは 404）。移行先は商用の Simcenter Radioss と、申請制の Radioss R&D プログラム（SCRDP、
Shared Source）。同日、Rocky Enterprise Software Foundation のコミュニティフォーク **OpenCourant** が発足
（https://opencourant.org/ 、https://github.com/OpenCourant/OpenCourant 、AGPL v3）。

## 影響

- 手元の Docker イメージ `clawstack-unified-openradioss:latest`（2026-06-15 版の公式リリース由来）は**そのまま動く**。
  INC-188 の計算は止まらない。
- ただし元の Dockerfile（clawstack_v2/docker/openradioss/Dockerfile）は公式 GitHub からダウンロードする作りなので、
  **同じ手順ではもう作り直せない**。手元の実行ファイルが唯一の原本。

## バックアップの場所（2026-10-11）

| 内容 | 場所 |
|---|---|
| 実行ファイル一式 `/opt/openradioss`（tar.gz、77 MB） | H:\clawstack_archive\openradioss_backup_20261011\opt_openradioss.tar.gz |
| Docker イメージ（docker save、180 MB） | 同上 \clawstack-unified-openradioss_latest.tar |
| OpenCourant の全履歴（bare ミラー、208 MB） | 同上 \OpenCourant.git |
| 上記＋オフライン用 Dockerfile＋復元手順 README＋運用スクリプト | GitHub 非公開 Yasu2019/openradioss-backup |
| OpenCourant ミラー | GitHub 非公開 Yasu2019/OpenCourant-mirror |
| 同じ一式 | Google Drive gdrive:OpenRadioss_backup_20261011/ |

## 復元

1. `cat image/*.part-* > openradioss.tar && docker load -i openradioss.tar`（イメージをそのまま戻す）
2. または `docker/Dockerfile`（tar.gz を ADD する、インターネット不要）で `docker build`
3. 将来ソースから作るなら OpenCourant。手元版（2026-06-15）と結果が一致するか、既存モデルで確かめてから切り替える。

## 教訓

外部の配布元に依存するビルド手順は、配布元が消えると再現できなくなる。使っているソルバーは、
実行ファイル・ライブラリ・設定ファイルを一式で手元と別の場所に控えておく。
