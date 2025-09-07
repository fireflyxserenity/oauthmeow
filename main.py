"""
Standalone OAuth Server for Railway
Handles Twitch OAuth and communicates with the bot via file writing
"""

import os
import requests
import logging
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# Store pending channel joins with timestamps for better reliability
pending_channels = []
processed_channels = []  # Keep track of what we've sent

# Environment variables
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID', 'i8doijnvc4wkt0q5et2fb7ucb7mng7')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

# Log startup info (without exposing secrets)
logging.info(f"Starting OAuth server...")
logging.info(f"Client ID: {TWITCH_CLIENT_ID}")
logging.info(f"Client Secret configured: {'Yes' if TWITCH_CLIENT_SECRET else 'No'}")
if not TWITCH_CLIENT_SECRET:
    logging.error("TWITCH_CLIENT_SECRET not found in environment variables!")

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

@app.route('/api/pending-channels', methods=['GET'])
def get_pending_channels():
    """Bot can poll this endpoint to get channels to join"""
    global pending_channels, processed_channels
    
    current_time = time.time()
    logging.info(f'Bot polling for channels. Current queue size: {len(pending_channels)}')
    
    # Only send channels that haven't been processed recently
    channels_to_send = []
    remaining_channels = []
    
    for channel_info in pending_channels:
        channel_age = current_time - float(channel_info.get('timestamp', 0))
        
        # Keep channels in queue for 5 minutes to allow multiple poll attempts
        if channel_age < 300:  # 5 minutes
            channels_to_send.append(channel_info)
            # Add to processed list to avoid sending duplicates
            if channel_info['channel'] not in [c.get('channel') for c in processed_channels]:
                processed_channels.append({
                    'channel': channel_info['channel'],
                    'processed_time': current_time
                })
        else:
            # Remove old channels after 5 minutes
            logging.warning(f"Removing old channel from queue: {channel_info['channel']}")
    
    # Clean up processed channels older than 1 hour
    processed_channels = [c for c in processed_channels if (current_time - c['processed_time']) < 3600]
    
    # Only keep channels newer than 5 minutes
    pending_channels = [c for c in pending_channels if (current_time - float(c.get('timestamp', 0))) < 300]
    
    logging.info(f'Sending {len(channels_to_send)} channels to bot: {[c["channel"] for c in channels_to_send]}')
    logging.info(f'Keeping {len(pending_channels)} channels in queue for retry')
    
    return jsonify({'channels': channels_to_send})

@app.route('/api/queue-status', methods=['GET'])
def queue_status():
    """Check current queue status"""
    global pending_channels, processed_channels
    current_time = time.time()
    
    # Format pending channels with age
    pending_with_age = []
    for channel in pending_channels:
        age = current_time - float(channel.get('timestamp', 0))
        pending_with_age.append({
            'channel': channel['channel'],
            'display_name': channel.get('display_name', ''),
            'age_seconds': int(age),
            'age_minutes': round(age / 60, 1)
        })
    
    return jsonify({
        'pending_channels': pending_with_age,
        'pending_count': len(pending_channels),
        'processed_recently': len(processed_channels),
        'server_time': current_time
    })

@app.route('/api/add-channel', methods=['POST'])
def add_channel_manually():
    """Manual endpoint to add channels"""
    data = request.get_json()
    if not data or 'channel' not in data:
        return jsonify({'success': False, 'error': 'Channel name is required'}), 400
    
    global pending_channels
    pending_channels.append({
        'channel': data['channel'],
        'display_name': data.get('display_name', data['channel']),
        'timestamp': data.get('timestamp', 'manual')
    })
    
    return jsonify({'success': True, 'message': f'Channel {data["channel"]} added to queue'})

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

        # Step 3: Notify the bot via webhook or queue
        # Add the channel to the pending queue for the bot to pick up
        logging.info(f'About to add channel {channel_name} to pending queue...')
        global pending_channels
        pending_channels.append({
            'channel': channel_name,
            'display_name': display_name,
            'user_id': user_data['id'],
            'timestamp': str(int(time.time()))
        })
        
        logging.info(f'Channel {channel_name} added to pending queue. Queue size: {len(pending_channels)}')
        logging.info(f'Current pending channels: {pending_channels}')
        
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
            else:
                logging.info(f'Channel queued for bot polling: {channel_name}')
        except Exception as e:
            logging.warning(f'Could not notify bot directly: {e}')
            # Channel is still in the queue for polling

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
    
    # Enhanced startup logging
    logging.info("=" * 50)
    logging.info("🚀 RAILWAY OAUTH SERVER STARTING UP")
    logging.info("=" * 50)
    logging.info(f"Port: {port}")
    logging.info(f"Host: 0.0.0.0")
    logging.info(f"Client ID: {TWITCH_CLIENT_ID}")
    logging.info(f"Client Secret: {'✅ CONFIGURED' if TWITCH_CLIENT_SECRET else '❌ MISSING'}")
    
    if not TWITCH_CLIENT_SECRET:
        logging.error("🔥 CRITICAL ERROR: TWITCH_CLIENT_SECRET not found!")
        logging.error("Check Railway environment variables in dashboard")
    else:
        logging.info("✅ All environment variables configured correctly")
    
    logging.info("🌐 Starting Flask server...")
    logging.info("=" * 50)
    
    app.run(host='0.0.0.0', port=port)
