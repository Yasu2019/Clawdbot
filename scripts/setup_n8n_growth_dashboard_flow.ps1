$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$workspaceDir = Join-Path $repoRoot "data\workspace"
$tempJsonPath = Join-Path $workspaceDir "temp_growth_dashboard_workflow.json"

# 1. Prepare workflow JSON
$workflowObj = @{
  name = "Growth Dashboard Daily Notification"
  active = $true
  nodes = @(
    @{
      id = "schedule_trigger"
      name = "Schedule Trigger"
      type = "n8n-nodes-base.scheduleTrigger"
      typeVersion = 1.1
      position = @(-200, 40)
      parameters = @{
        rule = "daily"
        time = "09:00"
        timezone = "Asia/Tokyo"
      }
    },
    @{
      id = "generate_report"
      name = "Generate Report"
      type = "n8n-nodes-base.code"
      typeVersion = 2
      position = @(40, 40)
      parameters = @{
        jsCode = @'
const ts = new Date().toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' });
return [{
  json: {
    title: '📈 Clawstack 自己成長レポート (定時)',
    message: `ミニPCが自律的に学習し、賢く成長しています！\n\n学習成果とPDCAサイクルの可視化は以下よりいつでもご確認いただけます。\n🔗 http://localhost:8088/apps/growth_dashboard/index.html\n\n【稼働中の自己成長システム】\n- 🧠 agent_self_growth_memory (Qdrantによる成功/失敗パターンの自律記憶と最適化)\n- 🕵️‍♂️ AI Strategy Scout (毎日09:40の最新トレンド自動スカウトと週次検討)\n- 🔄 自動 PDCA フィードバックリフレッシュの連続実行\n\n通知日時: ${ts}\n今日もミニPCは昨日より賢く、安定して自己成長を続けています！`,
    ntfyTopic: 'clawstack-watch'
  }
}];
'@
      }
    },
    @{
      id = "publish_ops_alert"
      name = "Publish Ops Alert"
      type = "n8n-nodes-base.httpRequest"
      typeVersion = 4.2
      position = @(280, 40)
      parameters = @{
        method = "POST"
        url = '=http://ntfy:80/{{$json.ntfyTopic}}'
        sendHeaders = $true
        headerParameters = @{
          parameters = @(
            @{ name = "Title"; value = '={{$json.title}}' },
            @{ name = "Priority"; value = "default" },
            @{ name = "Tags"; value = "chart_with_upwards_trend,brain" }
          )
        }
        sendBody = $true
        contentType = "raw"
        rawContentType = "text/plain"
        body = '={{$json.message}}'
        options = @{
          timeout = 15000
        }
      }
    }
  )
  connections = @{
    "Schedule Trigger" = @{
      main = , @(
        @(
          @{
            node = "Generate Report"
            type = "main"
            index = 0
          }
        )
      )
    }
    "Generate Report" = @{
      main = , @(
        @(
          @{
            node = "Publish Ops Alert"
            type = "main"
            index = 0
          }
        )
      )
    }
  }
  settings = @{
    executionOrder = "v1"
    saveManualExecutions = $true
    availableInMCP = $false
  }
}

# Write text as pure UTF-8 WITHOUT BOM using .NET WriteAllText to avoid JSON parse errors in n8n CLI
$jsonContent = $workflowObj | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText($tempJsonPath, $jsonContent)

# 2. Import the workflow JSON using container n8n CLI (let stderr output flow naturally, do not merge 2>&1)
Write-Output "Importing workflow into n8n via container CLI..."
docker exec -u root clawstack-unified-n8n-1 n8n import:workflow --input=/workspace/temp_growth_dashboard_workflow.json

# 3. Fetch the imported workflow ID from n8n CLI export (isolate stdout to prevent warnings merging)
Write-Output "Fetching imported workflow ID from n8n CLI export..."
$workflowsRaw = docker exec -u root clawstack-unified-n8n-1 n8n export:workflow --all

# Filter only valid JSON lines (starting with array [ or object {) to ensure robust parsing
$workflowsJson = ($workflowsRaw | Where-Object { $_ -match '^\s*[\[\{]' }) -join ""

if (-not $workflowsJson) {
  throw "Failed to extract valid JSON workflow list from n8n CLI."
}

$workflows = $workflowsJson | ConvertFrom-Json
$target = $workflows | Where-Object { $_.name -eq "Growth Dashboard Daily Notification" } | Select-Object -First 1
$workflowId = $target.id

if ($workflowId) {
  Write-Output "Successfully found imported workflow with ID: $workflowId. Activating..."
  # 4. Activate the workflow via container CLI
  docker exec -u root clawstack-unified-n8n-1 n8n update:workflow --id=$workflowId --active=true
  Write-Output "Successfully activated the daily growth notification workflow!"
} else {
  throw "Failed to retrieve imported workflow ID."
}

# 5. Cleanup temporary JSON file
if (Test-Path $tempJsonPath) {
  Remove-Item -Path $tempJsonPath -Force
}

Write-Output "All n8n deployment operations completed successfully via robust Container CLI!"
