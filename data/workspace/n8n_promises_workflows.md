# n8n Workflows for Promises Automation

You can import these JSON snippets into your n8n (<http://localhost:5679>) to automate the reports.

## 1. Daily Promises Report (23:00 JST)

```json
{
  "nodes": [
    {
      "parameters": {
        "rule": "0 23 * * *"
      },
      "name": "Schedule",
      "type": "n8n-nodes-base.cron",
      "typeVersion": 1,
      "position": [250, 300]
    },
    {
      "parameters": {
        "command": "docker exec clawstack-antigravity-1 node /work/data/workspace/scripts/send_email.js \"Daily Promises\" \"See PROMISES.md\""
      },
      "name": "Execute Command",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 1,
      "position": [450, 300]
    }
  ],
  "connections": {
    "Schedule": {
      "main": [
        [
          {
            "node": "Execute Command",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

## 2. API Billing Check (Every 30 mins)

```json
{
  "nodes": [
    {
      "parameters": {
        "rule": "*/30 * * * *"
      },
      "name": "Every 30 Mins",
      "type": "n8n-nodes-base.cron",
      "typeVersion": 1,
      "position": [250, 500]
    },
    {
      "parameters": {
        "command": "docker exec clawstack-antigravity-1 python3 /work/data/workspace/scripts/check_billing.py"
      },
      "name": "Check Billing",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 1,
      "position": [450, 500]
    }
  ],
  "connections": {
    "Every 30 Mins": {
      "main": [
        [
          {
            "node": "Check Billing",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```

## 3. Daily Quality Report (P016) - 00:00 JST

```json
{
  "nodes": [
    {
      "parameters": {
        "rule": "0 0 * * *"
      },
      "name": "Midnight Trigger",
      "type": "n8n-nodes-base.cron",
      "typeVersion": 1,
      "position": [250, 700]
    },
    {
      "parameters": {
        "command": "docker exec clawstack-antigravity-1 node /work/data/workspace/scripts/generate_quality_report.js"
      },
      "name": "Generate Report",
      "type": "n8n-nodes-base.executeCommand",
      "typeVersion": 1,
      "position": [450, 700]
    }
  ],
  "connections": {
    "Midnight Trigger": {
      "main": [
        [
          {
            "node": "Generate Report",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  }
}
```
