# Test Payloads

## IATF
```bash
curl -X POST http://127.0.0.1:18920/ask -H 'Content-Type: application/json' -d '{"query":"製造工程監査で8.5.1に関連する証跡は？","domain":"iatf"}'
```

## Drawing
```bash
curl -X POST http://127.0.0.1:18920/ask -H 'Content-Type: application/json' -d '{"query":"Datum C-Cの根拠と測定採用面を確認したい","domain":"drawing"}'
```

## QC Process
```bash
curl -X POST http://127.0.0.1:18920/ask -H 'Content-Type: application/json' -d '{"query":"プレス工程の管理項目と異常時処置は？","domain":"qc_process"}'
```
