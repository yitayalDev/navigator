# Backend Telegram Bot (uog navigetor)

This is a minimal Telegram-bot scaffold to expose campus locations and integrate with the app.

Setup (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a bot via BotFather and set the token as an environment variable:

```powershell
$env:UOG_NAVIGATOR_TELEGRAM_TOKEN = '123:ABC...'
python bot.py
```

Commands:
- `/start` - welcome message
- `/locations` - list known campus locations

You can extend `bot.py` to add inline queries, location-sharing, or integrate with a backend database.
