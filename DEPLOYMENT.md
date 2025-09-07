# Sparked Host Deployment Guide

## Files to Upload to Sparked Host

1. **meow_bot.py** - Main bot file with integrated OAuth server
2. **requirements.txt** - Python dependencies
3. **.env** - Environment variables (create from .env.example)
4. **channels_to_join.txt** - Empty file for channel management (will be created automatically)

## Environment Variables to Set in Sparked Host

Either create a `.env` file or set these environment variables in Sparked Host:

```
TWITCH_BOT_TOKEN=your_bot_token_here
TWITCH_CLIENT_ID=i8doijnvc4wkt0q5et2fb7ucb7mng7
TWITCH_CLIENT_SECRET=your_twitch_app_client_secret
TWITCH_CHANNELS=
BOT_PREFIX=!
```

## Website Configuration

### 1. Update HTML Files

You need to update the URLs in your HTML files to point to your Sparked Host instance:

In **twitch.html**, change:
```html
redirect_uri=https://your-github-pages-url.github.io/your-repo-name/twitch-auth.html
```

In **twitch-auth.html**, change:
```javascript
fetch('https://your-sparked-host-url.com/api/authorize-bot', {
```

### 2. GitHub Pages Setup

Upload these files to your GitHub Pages repository:
- twitch.html (main page)
- twitch-auth.html (OAuth callback handler)

## Quick Setup Steps

### For Sparked Host:

1. **Deploy to Sparked Host:**
   - Upload: `meow_bot.py`, `requirements.txt`, `.env`
   - Set environment variables or upload your `.env` file
   - Start the bot - it will run on whatever domain Sparked Host gives you

2. **Update your website:**
   - In `twitch-auth.html`, replace `https://your-sparked-host-domain.com` with your actual Sparked Host URL
   - Upload both HTML files to `fireflydesigns.me`

3. **Test:**
   - Visit `https://fireflydesigns.me/twitch.html`
   - Click "Add Bot to Channel"

## Troubleshooting

- **Bot not connecting:** Check TWITCH_BOT_TOKEN is valid
- **OAuth failing:** Verify TWITCH_CLIENT_SECRET is correct
- **Website errors:** Ensure URLs point to your actual Sparked Host domain
- **Bot not joining:** Check logs for file write permissions

## Support

The bot includes comprehensive logging. Check the console output for any error messages.
