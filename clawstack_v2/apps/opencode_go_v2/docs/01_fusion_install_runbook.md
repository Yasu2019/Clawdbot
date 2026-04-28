# 融合インストール手順書

## 配置
既存フォルダを上書きせず、隣に配置してください。

```text
clawstack-unified/
  opencode_go_clawstack_honki/
  opencode_go_clawstack_fusion_honki_v2/
```

## 推奨手順

```bash
git status
git checkout -b feature/opencode-go-fusion-v2
bash opencode_go_clawstack_fusion_honki_v2/scripts/git_backup_before_ai_change.sh
```

PowerShell確認:

```powershell
powershell -ExecutionPolicy Bypass -File .\opencode_go_clawstack_fusion_honki_v2\scripts\preflight_merge_check.ps1
```

## 取り込み優先順位
1. policies
2. agents
3. templates/db
4. templates/reports
5. configs/portal
6. configs/litellm

## 禁止
- docker-compose.ymlの全面自動書き換え
- 既存Portalカードの上書き
- OpenCode GOへの機密送信
- 本番環境への直接反映
