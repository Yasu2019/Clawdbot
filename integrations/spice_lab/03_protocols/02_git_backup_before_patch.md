# 大きな変更前のGitHub / Gitバックアップ手順

## 目的

AIエージェントが勝手にRailsアプリやPortalレイアウトを大きく書き換える事故を防ぎます。

## 変更前に必ず実行

```powershell
cd D:\Clawdbot_Docker_20260125
git status --short
git branch --show-current
git log --oneline -5
```

## 未コミット差分がない場合

```powershell
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
git checkout -b "backup/before-spice-lab-$ts"
git push -u origin "backup/before-spice-lab-$ts"
```

GitHubへpushできない場合でも、少なくともローカルブランチを残してください。

## 未コミット差分がある場合

差分を保存します。

```powershell
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
git diff > "backup_diff_before_spice_lab_$ts.patch"
git status --short > "backup_status_before_spice_lab_$ts.txt"
```

必要に応じて一時コミットします。

```powershell
git add -A
git commit -m "backup: before spice lab integration"
```

## AIエージェントへの禁止指示

- ユーザー承認なく `git reset --hard` しない
- ユーザー承認なく大量削除しない
- 既存UIを全面改修しない
- 既存composeを全面置換しない
- 競合時は新規compose overrideとして追加する
