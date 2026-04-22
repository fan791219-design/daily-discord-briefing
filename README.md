# Daily Discord Briefing

每天台北時間早上 9 點，透過 GitHub Actions 發送：

- 新竹縣竹北市當日天氣摘要
- 今日國際頭條 3 則中文摘要與連結
- 今日科技頭條 3 則中文摘要與連結
- Discord 通知

## 設定 Discord Webhook

1. 在 Discord 伺服器中選擇一個頻道。
2. 開啟頻道設定，進入 `Integrations` / `整合`。
3. 建立 `Webhook`，複製 Webhook URL。
4. 到 GitHub repo 的 `Settings` -> `Secrets and variables` -> `Actions`。
5. 新增 repository secret：
   - Name: `DISCORD_WEBHOOK_URL`
   - Secret: 你的 Discord Webhook URL

## 部署方式

把這個資料夾推到 GitHub repo 後，workflow 會在每天 09:00 Asia/Taipei 自動執行。

也可以手動測試：

1. 到 GitHub repo 的 `Actions`。
2. 選擇 `Daily Discord Briefing`。
3. 點 `Run workflow`。

## 資料來源

- 天氣：Open-Meteo forecast API
- 國際新聞：New York Times World RSS、CNN World RSS、CNN Latest RSS
- 科技新聞：New York Times Technology RSS、CNN Tech via Google News RSS
- 中文摘要：Google Translate public endpoint；若翻譯服務暫時不可用，會保留原文摘要

## 本機測試

```powershell
python scripts/daily_briefing.py --dry-run
```

這會印出 Discord 訊息內容，不會送出通知。
