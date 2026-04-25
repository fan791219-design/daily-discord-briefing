param(
  [Parameter(Mandatory = $true)]
  [string]$ProjectId,

  [string]$Location = "asia-east1",
  [string]$JobName = "daily-discord-briefing-dispatch",
  [string]$Owner = "fan791219-design",
  [string]$Repo = "daily-discord-briefing",
  [string]$EventType = "daily-discord-briefing"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
  throw "gcloud was not found. Install Google Cloud CLI before running this script."
}

$Token = $env:DAILY_DISCORD_GITHUB_TOKEN
if (-not $Token) {
  throw "Missing DAILY_DISCORD_GITHUB_TOKEN. Set it to a GitHub fine-grained PAT with Contents read/write access."
}

$Uri = "https://api.github.com/repos/$Owner/$Repo/dispatches"
$Body = @{
  event_type = $EventType
  client_payload = @{
    source = "google-cloud-scheduler"
    schedule = "asia-taipei-0900"
  }
} | ConvertTo-Json -Compress -Depth 5

$Headers = @(
  "Authorization=Bearer $Token",
  "Accept=application/vnd.github+json",
  "X-GitHub-Api-Version=2022-11-28",
  "Content-Type=application/json"
) -join ","

gcloud config set project $ProjectId | Out-Null
gcloud services enable cloudscheduler.googleapis.com --project $ProjectId | Out-Null

$ExistingJob = & gcloud scheduler jobs describe $JobName `
  --location $Location `
  --project $ProjectId `
  --format "value(name)" 2>$null

if ($ExistingJob) {
  gcloud scheduler jobs update http $JobName `
    --location $Location `
    --project $ProjectId `
    --schedule "0 9 * * *" `
    --time-zone "Asia/Taipei" `
    --uri $Uri `
    --http-method POST `
    --headers $Headers `
    --message-body $Body `
    --description "Trigger daily-discord-briefing through GitHub repository_dispatch at 09:00 Asia/Taipei."
} else {
  gcloud scheduler jobs create http $JobName `
    --location $Location `
    --project $ProjectId `
    --schedule "0 9 * * *" `
    --time-zone "Asia/Taipei" `
    --uri $Uri `
    --http-method POST `
    --headers $Headers `
    --message-body $Body `
    --description "Trigger daily-discord-briefing through GitHub repository_dispatch at 09:00 Asia/Taipei."
}

Write-Host "Google Cloud Scheduler job is ready."
Write-Host "Project:  $ProjectId"
Write-Host "Location: $Location"
Write-Host "Job:      $JobName"
Write-Host "Schedule: 0 9 * * * Asia/Taipei"
Write-Host "Test:     gcloud scheduler jobs run $JobName --location $Location --project $ProjectId"
