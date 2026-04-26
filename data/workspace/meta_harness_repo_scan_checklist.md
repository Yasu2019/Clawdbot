# Meta Harness Repo Scan Checklist

導入前に少なくとも次を確認する:

- `docker-compose*.yml`
- compose override / patch files
- env / policy files
- gateway / routing code
- benchmark / evaluation scripts
- n8n workflow 作成スクリプト
- Portal / dashboard UI
- Gmail / RAG / complaint / learning 関連コード
- approval / safety policy

記録する項目:

- location
- purpose
- maturity
- overlap level
- adoption decision

既定判断:

- overlap が高い場合は `ADOPT_PARTIAL`
- benefit が不明な場合は `HOLD`
- safety regression の恐れがある場合は `REJECT`
