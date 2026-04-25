# Google Cloud Scheduler Setup

Use Google Cloud Scheduler as the primary daily trigger for this repository. The Scheduler job calls GitHub's `repository_dispatch` endpoint, and the existing GitHub Actions workflow sends the Discord briefing.

## Schedule

- Primary trigger: Google Cloud Scheduler
- Time: `09:00 Asia/Taipei`
- Cron: `0 9 * * *`
- Backup trigger: GitHub Actions native schedule at `09:17 Asia/Taipei`
- Duplicate protection: the workflow saves a daily cache marker and skips later triggers on the same Taiwan date

## Required GitHub Token

Create a fine-grained personal access token:

- Repository access: only `fan791219-design/daily-discord-briefing`
- Repository permissions: `Contents: Read and write`
- Expiration: 90 or 180 days is recommended

Store the token only in your local environment or in Google Cloud Scheduler headers. Do not commit it.

PowerShell example:

```powershell
setx DAILY_DISCORD_GITHUB_TOKEN "YOUR_GITHUB_FINE_GRAINED_TOKEN"
```

Open a new PowerShell window after running `setx`, or set it only for the current terminal:

```powershell
$env:DAILY_DISCORD_GITHUB_TOKEN = "YOUR_GITHUB_FINE_GRAINED_TOKEN"
```

## Create The Scheduler Job

Install and authenticate the Google Cloud CLI first:

```powershell
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
gcloud services enable cloudscheduler.googleapis.com
```

Then run:

```powershell
.\scripts\create-google-cloud-scheduler-job.ps1 `
  -ProjectId "YOUR_GCP_PROJECT_ID" `
  -Location "asia-east1"
```

The helper creates or updates this job:

- Job name: `daily-discord-briefing-dispatch`
- URL: `https://api.github.com/repos/fan791219-design/daily-discord-briefing/dispatches`
- Method: `POST`
- Body:

```json
{"event_type":"daily-discord-briefing","client_payload":{"source":"google-cloud-scheduler","schedule":"asia-taipei-0900"}}
```

## Manual Test

Run the Scheduler job once:

```powershell
gcloud scheduler jobs run daily-discord-briefing-dispatch --location asia-east1
```

Then check:

- GitHub Actions has a new `repository_dispatch` run
- The run logs show `payload_source=google-cloud-scheduler`
- Discord receives the briefing

Run it a second time on the same day to confirm duplicate protection. The second run should restore the daily cache marker and skip Discord delivery.

## Troubleshooting

- `401` or `403`: the GitHub token is missing, expired, or does not have `Contents: Read and write`.
- `404`: the token cannot access `fan791219-design/daily-discord-briefing`, or the owner/repo is wrong.
- Scheduler job succeeds but no Discord message appears: open the GitHub Actions run and check whether it skipped because today's cache marker already exists.
- No Scheduler run appears: confirm Cloud Scheduler API is enabled and the job location matches the location used by `gcloud scheduler jobs run`.
