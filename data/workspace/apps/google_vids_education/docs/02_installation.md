# 02 Installation: Clawstackへの後付け導入手順

## 1. 配置先

推奨配置:

```bash
mkdir -p ~/clawstack/extensions/google_vids_openclaw_education
cp -r . ~/clawstack/extensions/google_vids_openclaw_education/
```

Windows側から配置する場合:

```powershell
mkdir C:\clawstack\extensions\google_vids_openclaw_education
```

## 2. Portalカード追加

`portal_card/google_vids_education_card.html` を既存Portalのlocal apps領域に配置します。

例:

```bash
cp portal_card/google_vids_education_card.html ~/clawstack/portal/apps/google_vids_education/index.html
```

Portal側のカード登録方式がJSONの場合は、`portal_card/portal_card_manifest.json` を既存manifestに追記してください。

## 3. OpenClaw workflow登録

`openclaw_workflows/education_video_pipeline.yaml` をOpenClawのworkflow定義フォルダへコピーします。

```bash
cp openclaw_workflows/education_video_pipeline.yaml ~/clawstack/openclaw/workflows/
```

## 4. RAGスキーマ登録

`rag_schemas/education_video_metadata.schema.json` を教材生成用メタデータとして使います。

重要フィールド:
- source_doc_id
- process
- defect_type
- iatf_clause
- confidentiality_level
- approval_status

## 5. Node-RED連携

`nodered/flow_google_vids_education.json` は、将来的に以下を自動化するための雛形です。

- 新しい不具合報告書を検知
- 教材化候補としてPortalに通知
- 承認済み台本を保存

Node-REDのImportからJSONを読み込んでください。

## 6. 動作確認

```bash
python scripts/generate_vids_package.py --input samples/sample_defect_case.yaml --output out_sample
```

生成されるもの:
- script.md
- storyboard.md
- google_vids_prompt.md
- review_sheet.md
