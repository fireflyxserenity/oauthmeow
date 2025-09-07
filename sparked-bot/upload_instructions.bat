@echo off
echo Uploading updated bot to Sparked Host...
echo.
echo Files to upload:
echo - meow_bot.py (updated with Railway polling)
echo - .env (with Railway API URL)
echo - requirements.txt (add requests if not present)
echo.
echo Manual steps needed:
echo 1. Upload these files to your Sparked Host via Apollo control panel
echo 2. Restart the bot in Apollo
echo 3. Check logs to confirm Railway API polling is working
echo.
pause
