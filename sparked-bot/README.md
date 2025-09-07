# Sparked Host Bot

This folder contains the simplified Twitch bot for Sparked Host deployment.

## Files:
- `meow_bot.py` - Main bot file (simplified, no Flask)
- `requirements.txt` - TwitchIO dependencies only
- `.env` - Bot token and initial channels
- `channels_to_join.txt` - Auto-created for new channel joins

## Features:
✅ All meow counting and commands
✅ Multi-channel support
✅ Automatic channel joining via file watching
✅ SQLite database with analytics
✅ All original commands: !meowstats, !topmew, !globalmew, !meowinfo

## Deployment to Sparked Host:
1. Upload these files
2. Make sure .env has correct TWITCH_BOT_TOKEN
3. Run: `python meow_bot.py`
