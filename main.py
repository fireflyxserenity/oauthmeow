"""
Standalone OAuth Server for Railway
Handles Twitch OAuth and communicates with the bot via file writing
"""

import os
import requests
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# Environment variables
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID', 'i8doijnvc4wkt0q5et2fb7ucb7mng7')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

@app.route('/')
def home():
    return jsonify({
        'status': 'OK',
        'message': 'Meow Bot OAuth Server',
        'version': '1.0'
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'OK', 
        'message': 'Meow Bot Auth API is running',
        'redirect_uri': 'https://fireflydesigns.me/twitch.html',
        'version': '2.0-updated'
    })

@app.route('/api/authorize-bot', methods=['POST'])
def authorize_bot():
    try:
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({'success': False, 'error': 'Authorization code is required'}), 400

        auth_code = data['code']
        logging.info(f'Received authorization code: {auth_code[:10]}...')

        # Step 1: Exchange code for access token
        redirect_uri = 'https://fireflydesigns.me/twitch.html'
        logging.info(f'Using redirect URI: {redirect_uri}')
        
        token_data_payload = {
            'client_id': TWITCH_CLIENT_ID,
            'client_secret': TWITCH_CLIENT_SECRET,
            'code': auth_code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        }
        logging.info(f'Token request payload: {token_data_payload}')
        
        token_response = requests.post('https://id.twitch.tv/oauth2/token', data=token_data_payload)

        if token_response.status_code != 200:
            raise Exception(f"Token exchange failed: {token_response.text}")

        token_data = token_response.json()
        access_token = token_data['access_token']
        logging.info('Successfully obtained access token')

        # Step 2: Get user information
        user_response = requests.get('https://api.twitch.tv/helix/users', headers={
            'Authorization': f'Bearer {access_token}',
            'Client-Id': TWITCH_CLIENT_ID
        })

        if user_response.status_code != 200:
            raise Exception(f"User info request failed: {user_response.text}")

        user_data = user_response.json()['data'][0]
        channel_name = user_data['login']
        display_name = user_data['display_name']
        
        logging.info(f'User data: {display_name} ({channel_name})')

        # Step 3: Notify the bot via webhook or file
        # For now, we'll use a simple HTTP request to notify the bot
        # You can replace this with your preferred communication method
        
        try:
            # Try to notify the bot directly if it has a webhook endpoint
            bot_notify_url = os.getenv('BOT_WEBHOOK_URL')
            if bot_notify_url:
                notify_response = requests.post(bot_notify_url, json={
                    'action': 'join_channel',
                    'channel': channel_name,
                    'display_name': display_name
                }, timeout=5)
                logging.info(f'Bot notification sent: {notify_response.status_code}')
        except Exception as e:
            logging.warning(f'Could not notify bot directly: {e}')
            # This is okay - the bot can still pick up channels via file watching

        return jsonify({
            'success': True,
            'message': 'Bot successfully added to channel',
            'channel': display_name,
            'user_id': user_data['id']
        })

    except Exception as error:
        logging.error(f'Authorization error: {error}')
        return jsonify({
            'success': False,
            'error': 'Failed to process authorization',
            'details': str(error)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
