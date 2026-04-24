# n8n Automation Blueprint

## Workflow A: Nightly QA Document Digest
Trigger:
- Cron nightly

Flow:
1. Get list of new files from Paperless or watched folder
2. Extract text / metadata
3. Privacy classify
4. Retrieve related chunks from Qdrant
5. If low-risk -> Kimi worker route
6. Reviewer model check
7. Save digest markdown
8. Notify via portal or email draft

## Workflow B: Incoming Nonconformity Assistant
Trigger:
- new NCR/CAPA document

Flow:
1. Parse document
2. Extract issue, evidence, dates, owners
3. Retrieve similar past cases
4. Kimi creates first-pass issue summary
5. reviewer model checks wording
6. create internal task artifact

## Workflow C: Defect Trend Analyzer
Trigger:
- daily / on-demand

Flow:
1. read defect data source
2. calculate trend metrics in script node
3. Kimi explains patterns in plain Japanese
4. reviewer model converts into manager-ready summary
5. archive result

## Required n8n controls
- environment variable kill switch: KIMI_ENABLED=false
- max retry count
- timeout per HTTP/model node
- error branch to alert channel
- separate branch for local-only mode
