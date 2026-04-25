# Daily Discord Briefing

每天台北時間早上 9 點，透過 Google Cloud Scheduler 觸發 GitHub Actions，發送：

- 新竹縣竹北市當日天氣摘要
- 今日國際頭條 3 則中文摘要與連結
- 今日科技頭條 3 則中文摘要與連結
- Discord 通知

## 排程策略

主力排程是 Google Cloud Scheduler，在每天 `09:00 Asia/Taipei` 呼叫 GitHub `repository_dispatch`。

GitHub Actions 原生 `schedule` 保留為備援，在每天 `09:17 Asia/Taipei` 觸發。workflow 會用台灣日期建立每日 sent marker，同一天如果被 Google Cloud Scheduler、GitHub schedule、或手動測試重複觸發，後續 run 會自動跳過 Discord 發送。

Gemini API key 不用在排程觸發流程；這裡需要的是 Google Cloud Scheduler 與可呼叫 GitHub `repository_dispatch` 的 GitHub fine-grained token。

## 設定 Discord Webhook

1. 在 Discord 伺服器中選擇一個頻道。
2. 開啟頻道設定，進入 `Integrations` / `整合`。
3. 建立 `Webhook`，複製 Webhook URL。
4. 到 GitHub repo 的 `Settings` -> `Secrets and variables` -> `Actions`。
5. 新增 repository secret：
   - Name: `DISCORD_WEBHOOK_URL`
   - Secret: 你的 Discord Webhook URL

## 設定 Google Cloud Scheduler

完整設定步驟請看 [docs/google-cloud-scheduler.md](docs/google-cloud-scheduler.md)。

最短流程：

1. 建立 GitHub fine-grained personal access token。
2. token repository access 只選 `fan791219-design/daily-discord-briefing`。
3. token repository permission 設定 `Contents: Read and write`。
4. 在本機設定環境變數 `DAILY_DISCORD_GITHUB_TOKEN`。
5. 執行 helper script 建立 Cloud Scheduler job：

```powershell
.\scripts\create-google-cloud-scheduler-job.ps1 -ProjectId "YOUR_GCP_PROJECT_ID" -Location "asia-east1"
```

## 手動測試

本機測試 `repository_dispatch`：

```powershell
.\scripts\trigger-daily-discord-briefing.ps1 -Source local-test
```

手動執行 Google Cloud Scheduler job：

```powershell
gcloud scheduler jobs run daily-discord-briefing-dispatch --location asia-east1
```

也可以從 GitHub Actions 頁面手動測試：

1. 到 GitHub repo 的 `Actions`。
2. 選擇 `Daily Discord Briefing`。
3. 點 `Run workflow`。

## 資料來源

- 天氣：Open-Meteo forecast API
- 國際新聞：New York Times World RSS、CNN World RSS、CNN Latest RSS
- 科技新聞：New York Times Technology RSS、CNN Tech via Google News RSS
- 中文摘要：Google Translate public endpoint；若翻譯服務暫時不可用，會保留原文摘要

## 本機 dry run

```powershell
python -m pip install -r requirements.txt
python scripts/daily_briefing.py --dry-run
```

這會印出 Discord 訊息內容，不會送出通知。
