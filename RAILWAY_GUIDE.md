# Railway Deployment Guide for OAuth Server

## Quick Setup Steps:

### 1. Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub
3. Connect your GitHub account

### 2. Deploy OAuth Server to Railway
1. Create a new GitHub repository for the OAuth server
2. Upload these files to the repo:
   - `oauth_server.py`
   - `oauth_requirements.txt` (rename to `requirements.txt`)
   - `oauth.env` (rename to `.env`)

3. In Railway:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your OAuth server repo
   - Railway will auto-detect it's a Python app

### 3. Set Environment Variables in Railway
In your Railway project dashboard, go to Variables and add:
- `TWITCH_CLIENT_ID=i8doijnvc4wkt0q5et2fb7ucb7mng7`
- `TWITCH_CLIENT_SECRET=tekkjeuxfehsa039o60hfbxeknvnln`

### 4. Get Your Railway URL
After deployment, Railway will give you a URL like:
`https://meowbot-oauth.up.railway.app`

### 5. Update Your Website
Replace the URL in `twitch-auth.html` with your actual Railway URL:
```javascript
fetch('https://your-actual-railway-url.up.railway.app/api/authorize-bot', {
```

### 6. Update Bot on Sparked Host
Replace `meow_bot.py` with `meow_bot_simple.py` and update `requirements.txt` to `bot_requirements.txt`

## File Structure:

### For Railway (OAuth Server):
```
oauth-server/
├── oauth_server.py (main file)
├── requirements.txt (Flask dependencies)
└── .env (Twitch secrets)
```

### For Sparked Host (Bot):
```
bot/
├── meow_bot_simple.py (main file)
├── requirements.txt (TwitchIO dependencies)
├── .env (bot token and channels)
└── channels_to_join.txt (auto-created)
```

## Testing:
1. Test OAuth server: Visit `https://your-railway-url.up.railway.app/api/health`
2. Test full flow: Go through the website OAuth process
3. Bot should automatically join the channel via file watching

This hybrid approach gives you:
✅ Easy public OAuth server (Railway)
✅ Reliable bot hosting (Sparked Host)
✅ Simple deployment and maintenance
