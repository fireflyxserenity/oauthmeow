# Railway OAuth Server

This folder contains the OAuth server that handles Twitch authorization.

## Files:
- `main.py` - Flask OAuth server
- `requirements.txt` - Python dependencies 
- `.env` - Environment variables (Twitch secrets)

## Deployment:
1. Push this folder to a GitHub repository
2. Connect to Railway
3. Set environment variables in Railway dashboard
4. Get public URL and update website

## Environment Variables Needed in Railway:
- `TWITCH_CLIENT_ID=i8doijnvc4wkt0q5et2fb7ucb7mng7`
- `TWITCH_CLIENT_SECRET=tekkjeuxfehsa039o60hfbxeknvnln`
