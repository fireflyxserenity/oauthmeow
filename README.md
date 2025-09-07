# Twitch Meow Counter Bot

A Python bot for Twitch that counts "meow" messages in chat and provides various statistics and commands.

## Features

- **Automatic Meow Detection**: Counts every "meow" in chat messages (case-insensitive)
- **Per-User Tracking**: Tracks meows per user per channel
- **Stream Session Tracking**: Counts meows for current stream (daily reset)
- **All-Time Streamer Stats**: Total meows across all time for each streamer
- **Global Leaderboard**: Opt-in leaderboard comparing streamers
- **Persistent Storage**: SQLite database saves all data between bot restarts

## Commands

- `!meow` - Check your personal meow count in this channel
- `!totalmeows` - Show all-time meows for this streamer
- `!streammeows` - Show meows for today's stream session
- `!globalleaderboard` - Display top 5 streamers (opted-in only)
- `!optinglobal` - Opt into global leaderboard (broadcaster only)
- `!optoutglobal` - Opt out of global leaderboard (broadcaster only)
- `!meowhelp` - Show all available commands

## Setup Instructions

### 1. Get a Twitch Bot Token

**UPDATED 2025**: The old twitchapps.com/tmi/ is discontinued. Use these methods:

**Option A - Alternative Generator (Easiest):**
1. Go to [https://twitchtokengenerator.com/](https://twitchtokengenerator.com/)
2. Select "Chat Bot" and click "Generate Token"
3. **Log in with your BOT account** (not your main account)
4. Copy the OAuth token (starts with `oauth:`)

**Option B - Official Twitch Console:**
1. Create app at [dev.twitch.tv/console](https://dev.twitch.tv/console)
2. Use the manual steps in `TOKEN_SETUP.md`

**Option C - Use Token Helper:**
```bash
python get_token.py
```

### 2. Configure the Bot

1. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```

2. Edit `.env` and fill in your information:
   ```
   TWITCH_BOT_TOKEN=oauth:your_token_here
   TWITCH_CHANNELS=your_channel,friend_channel
   BOT_PREFIX=!
   ```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Bot

```bash
python meow_bot.py
```

## Database

The bot creates a `meow_counts.db` SQLite file with the following tables:

- `user_meows` - Meow counts per user per channel
- `stream_meows` - Daily meow counts per channel
- `streamer_totals` - All-time meow totals per channel
- `channel_settings` - Channel preferences (global leaderboard opt-in)

## How It Works

1. **Message Monitoring**: Bot listens to all chat messages in connected channels
2. **Meow Detection**: Uses regex to find "meow" words (case-insensitive, whole words only)
3. **Automatic Counting**: Each detected meow increments counters for:
   - The user who said it
   - The current stream session
   - The streamer's all-time total
4. **Instant Feedback**: Bot responds with current stream meow count
5. **Command Responses**: Users can query various statistics

## Multi-Channel Support

- Bot can join multiple channels simultaneously
- Each channel has independent meow tracking
- Streamers can individually opt in/out of global leaderboard
- Database keeps all data separate by channel

## Privacy & Opt-in

- Global leaderboard is **opt-in only**
- Only broadcasters can enable/disable global participation
- Individual user data stays within each channel
- No personal data is shared between channels

## Logging

The bot creates a `meow_bot.log` file with:
- Connection status
- Meow detection events
- Command usage
- Error messages

## Troubleshooting

### Bot won't connect
- Verify your token is correct and starts with `oauth:`
- Check that channel names don't include the `#` symbol
- Ensure the bot account has chat permissions

### Database issues
- The bot will create `meow_counts.db` automatically
- If corrupted, delete the file and restart (data will be lost)
- Database is portable - you can backup/restore the `.db` file

### Commands not working
- Verify the prefix matches your `.env` setting
- Commands are case-sensitive
- Some commands require broadcaster permissions

## Development

The bot is built with:
- **TwitchIO**: Official Twitch IRC library for Python
- **SQLite**: Embedded database for persistence
- **Asyncio**: Asynchronous event handling

Feel free to modify the code to add new features or customize behavior!
