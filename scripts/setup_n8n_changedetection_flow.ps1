$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$stateDir = Join-Path $repoRoot "data\state\n8n_changedetection_flow"
$configPath = Join-Path $stateDir "config.json"
$statusPath = Join-Path $stateDir "harness_status.json"

$n8nBaseUrl = "http://127.0.0.1:5679"
$n8nApiKey = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
$webhookPath = "changedetection-bridge"
$workflowName = "Changedetection Bridge Intake"

function Write-Status {
  param([string]$State, [hashtable]$Extra = @{})
  $payload = @{
    service = "n8n_changedetection_flow_setup"
    updatedAt = (Get-Date).ToString("o")
    state = $State
  }
  foreach ($key in $Extra.Keys) {
    $payload[$key] = $Extra[$key]
  }
  $payload | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 $statusPath
}

function Invoke-N8nApi {
  param(
    [string]$Method,
    [string]$Path,
    $Body = $null
  )
  $headers = @{ "X-N8N-API-KEY" = $n8nApiKey }
  $params = @{
    Method = $Method
    Uri = "$n8nBaseUrl$Path"
    Headers = $headers
    TimeoutSec = 300
  }
  if ($null -ne $Body) {
    $params["ContentType"] = "application/json"
    $params["Body"] = ($Body | ConvertTo-Json -Depth 20)
  }
  return Invoke-RestMethod @params
}

function Enable-N8nWorkflow {
  param(
    [string]$WorkflowId,
    [string]$WorkflowVersionId
  )

  try {
    Invoke-N8nApi -Method "POST" -Path "/api/v1/workflows/$WorkflowId/activate" -Body @{
      versionId = $WorkflowVersionId
      name = $workflowName
    } | Out-Null
    return "api"
  } catch {
    docker exec clawstack-unified-n8n-1 n8n update:workflow --id=$WorkflowId --active=true | Out-Null
    return "cli"
  }
}

function New-WorkflowBody {
  $webhookId = [guid]::NewGuid().ToString()
  return @{
    name = $workflowName
    nodes = @(
      @{
        id = "webhook_changedetection"
        webhookId = $webhookId
        name = "Changedetection Webhook"
        type = "n8n-nodes-base.webhook"
        typeVersion = 2.1
        position = @(-220, 40)
        parameters = @{
          httpMethod = "POST"
          path = $webhookPath
          responseMode = "responseNode"
          options = @{}
        }
      },
      @{
        id = "normalize_event"
        name = "Normalize Event"
        type = "n8n-nodes-base.code"
        typeVersion = 2
        position = @(20, 40)
        parameters = @{
          jsCode = @'
const body = $json.body || $json;
const ts = new Date().toISOString();
const title = body.title || body.watchTitle || body.url || 'Changedetection update';
const url = body.url || body.watchUrl || '';
const source = body.source || 'changedetection-bridge';
const summary = body.summary || `Changedetection detected an update for ${title}`;
const checkedAt = body.checkedAt || body.lastChecked || ts;
const taskId = body.taskId ?? null;
const ntfyTopic = body.ntfyTopic || 'clawstack-watch';

return [{
  json: {
    source,
    title,
    url,
    summary,
    checkedAt,
    taskId,
    ntfyTopic,
    receivedAt: ts,
    dashboardUrl: 'http://127.0.0.1:4001',
    vikunjaUrl: 'http://127.0.0.1:3456',
    changedetectionUrl: 'http://127.0.0.1:5081'
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
              @{ name = "Title"; value = '=Automation intake: {{$json.title}}' },
              @{ name = "Priority"; value = "default" },
              @{ name = "Tags"; value = "satellite,triangular_flag_on_post" }
            )
          }
          sendBody = $true
          contentType = "raw"
          rawContentType = "text/plain"
          body = @'
=Source: {{$json.source}}
Title: {{$json.title}}
URL: {{$json.url}}
Task: {{$json.taskId || "none"}}
Checked: {{$json.checkedAt}}
Received: {{$json.receivedAt}}
Dashy: {{$json.dashboardUrl}}
'@
          options = @{
            timeout = 15000
          }
        }
      },
      @{
        id = "respond_success"
        name = "Respond Success"
        type = "n8n-nodes-base.respondToWebhook"
        typeVersion = 1.1
        position = @(560, 40)
        parameters = @{
          respondWith = "json"
          responseBody = @'
={{ JSON.stringify({
  ok: true,
  title: $json.title,
  url: $json.url,
  taskId: $json.taskId || "",
  receivedAt: $json.receivedAt
}) }}
'@
          options = @{
            responseCode = 200
          }
        }
      }
    )
    connections = @{
      "Changedetection Webhook" = @{
        main = , @(
          @(
            @{
              node = "Normalize Event"
              type = "main"
              index = 0
            }
          )
        )
      }
      "Normalize Event" = @{
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
      "Publish Ops Alert" = @{
        main = , @(
          @(
            @{
              node = "Respond Success"
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
}

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null
Write-Status -State "starting"

$existing = Invoke-N8nApi -Method "GET" -Path "/api/v1/workflows"
$workflow = $existing.data | Where-Object { $_.name -eq $workflowName } | Select-Object -First 1
$workflowVersionId = $null

if ($workflow) {
  Invoke-N8nApi -Method "DELETE" -Path "/api/v1/workflows/$($workflow.id)" | Out-Null
}

$workflowBody = New-WorkflowBody
$created = Invoke-N8nApi -Method "POST" -Path "/api/v1/workflows" -Body $workflowBody
$workflowId = $created.id
$workflowVersionId = $created.versionId

$activationMode = Enable-N8nWorkflow -WorkflowId $workflowId -WorkflowVersionId $workflowVersionId

$config = @{
  updatedAt = (Get-Date).ToString("o")
  n8n = @{
    baseUrl = $n8nBaseUrl
    workflowId = $workflowId
    versionId = $workflowVersionId
    workflowName = $workflowName
    webhookPath = $webhookPath
    webhookUrl = "$n8nBaseUrl/webhook/$webhookPath"
  }
}
$config | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 $configPath

Write-Status -State "ready" -Extra @{
  workflowId = $workflowId
  webhookUrl = $config.n8n.webhookUrl
  activationMode = $activationMode
}

$config | ConvertTo-Json -Depth 10
