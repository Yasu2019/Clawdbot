# Clawstack トラブルログ

> **注意**: 過去トラブルの正式記録は `memory/trouble_history.md` が本ファイルです。
> このファイルは 2026-04-10 に作成しましたが、重複のため今後は `memory/trouble_history.md` に一本化してください。
> → **参照先**: `D:\Clawdbot_Docker_20260125\data\workspace\memory\trouble_history.md`

---

## [CRITICAL] 2026-04-10 ジャンクションポイントを重複データと誤認して削除

### 概要
`E:\ClawstackData\clawstack_v2_data` を「重複データ」と誤判断して `rm -rf` 実行。
実際は `clawstack_v2\data` の**Windowsジャンクションポイントのターゲット**であり、本物のデータだった。

### 根本原因
```
D:\Clawdbot_Docker_20260125\clawstack_v2\data  ← Junctionポイント
  └── (実体) → E:\ClawstackData\clawstack_v2_data  ← 本物
```
- `du -sh` を両パスで実行したところ同一サイズ（Ollama 53GB / Paperless 41GB / Qdrant 5.9GB 等）が表示
- 同一サイズ＝重複コピーと誤認 → E ドライブ側を削除

### なぜ助かったか
- Docker Desktop（WSL2バックエンド）は bind mount データを **WSL2 VHD**（`E:\DockerData\DockerDesktopWSL\`）に保存する
- Gitbash の `rm -rf`（Windows API）は Windows ディレクトリエントリを削除するが、**WSL2 VHD 内の実データには届かない**
- 実行中コンテナは WSL2 VHD 経由でデータにアクセスし続けた

### 被害
- Qdrant `iatf_knowledge`: 768-dim データが一時喪失 → バックアップ JSON から 1024-dim で再構築済み
- `E:\ClawstackData\clawstack_v2_data` ディレクトリが再作成されるまで Qdrant 再起動不可
- その他サービスデータは無事（WSL2 VHD 内で保全）

### 再発防止チェックリスト

**大量削除・移動の前に必ず実施：**

```powershell
# 1. Junctionポイントの確認（必須！）
Get-ChildItem 'D:\Clawdbot_Docker_20260125' -Recurse -Depth 3 -Force |
  Where-Object { $_.LinkType -eq 'Junction' } |
  Select-Object FullName, LinkType, Target

# 2. Docker コンテナのマウント確認
docker inspect $(docker ps -q) --format '{{.Name}}: {{json .Mounts}}' |
  python3 -c "import sys; [print(l) for l in sys.stdin]"

# 3. ディスク使用量の二重確認（同サイズ＝要注意）
du -sh /d/Clawdbot_Docker_20260125/clawstack_v2/data/*/
du -sh /e/ClawstackData/clawstack_v2_data/*/
```

**ルール：**
- `du` で同一サイズのディレクトリが2箇所にある場合、**必ずジャンクション/シンリンクを確認**してから削除
- Docker コンテナが使用中のパスは絶対に削除しない（`docker inspect` でマウント確認）
- 大量削除は `docker compose stop` 後に実施
- E ドライブ上の `clawstack_v2_data` は本物のデータ（Junctionターゲット）

### 関連パス（現状）
```
clawstack_v2\data  →  Junction  →  E:\ClawstackData\clawstack_v2_data
E:\DockerData\DockerDesktopWSL\  →  WSL2 VHD（Docker実データ保存場所）
```

---

## [WARNING] 2026-04-10 Windows TEMP が E ドライブを指していた

### 概要
ユーザー環境変数 `TEMP`/`TMP` が `E:\ClawstackData\LocalTemp` に設定されていた。
Claude Code バックグラウンドタスクがこのパスに出力ファイルを書き込むため、
`LocalTemp` の `rm -rf` 中にタスク出力ファイルがロックされ、削除が不完全になった。

### 対処
`TEMP`/`TMP` を `D:\Temp` に変更済み（2026-04-10）。

```powershell
[System.Environment]::SetEnvironmentVariable('TEMP', 'D:\Temp', 'User')
[System.Environment]::SetEnvironmentVariable('TMP', 'D:\Temp', 'User')
```

---

## [INFO] 2026-04-10 SSD 構成の確認（GPU アダプター検討関連）

### 物理構成
| ドライブ | モデル | 接続 | 速度 |
|---|---|---|---|
| C: / D: | Crucial CT1000E100SSD8 | NVMe PCIe 4.0 x4 | 高速 |
| E: | KIOXIA EXCERIA BASIC | NVMe PCIe 4.0 x4 | 標準 |
| (空き) | — | 未確認（SATA or PCIe x2 の可能性） | — |

- C と D は同一物理 SSD（パーティション分割）
- 高 I/O データ（Docker/Ollama/Qdrant）は D（Crucial）推奨
- アーカイブ/低頻度データのみ E（KIOXIA）または D に移動可
- 空きスロットへの GPU アダプター接続は物理確認が必要（Key M / Key B+M の確認）

---
