# 導入手順

## 1. まず展開
ZIPを `C:\clawstack\para_openclaw` などに展開します。

## 2. dry-runで分類確認
```powershell
cd C:\clawstack\para_openclaw\04_Autonomous_Agent\scripts
python para_autonomous_router.py --base C:\clawstack\para_openclaw --dry-run
```

## 3. inboxへ試験ファイルを置く
`02_PARA_Vault/90_Inbox` にPDF、CSV、Markdown、Excelなどを少量置いてテストします。

## 4. 実移動はバックアップ後
```powershell
python para_autonomous_router.py --base C:\clawstack\para_openclaw --apply
```

## 5. Node-RED連携
`05_IoT_NodeRED/flows/para_iot_flow_template.json` をNode-REDにインポートし、CSV保存先を `90_Inbox/iot_logs` に設定します。

## 6. Qdrant/Paperless連携
まずはテンプレートを既存のClawstack構成に合わせてCodex/Claudeに読ませ、差分パッチとして導入してください。
