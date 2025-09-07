"""
Twitch Meow Counter Bot - OAuth Version

A Twitch IRC bot that counts "meow" messages in chat and provides various commands
to check meow statistics per user, per channel, and globally across streamers.

Features:
- Automatic channel joining via OAuth
- Free global leaderboard access for all channels
- Smart overlapping meow detection
- Real-time meow counting and statistics
"""

import os
import re
import sqlite3
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from twitchio.ext import commands
from dotenv import load_dotenv
import logging
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('meow_bot.log'),
        logging.StreamHandler()
    ]
)

# Flask app for OAuth backend
flask_app = Flask(__name__)
CORS(flask_app)

# Twitch API Configuration for OAuth
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID', 'i8doijnvc4wkt0q5et2fb7ucb7mng7')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

if not TWITCH_CLIENT_SECRET:
    logging.error('ERROR: TWITCH_CLIENT_SECRET environment variable is required')
    exit(1)

@flask_app.route('/api/authorize-bot', methods=['POST'])
def authorize_bot():
    try:
        data = request.get_json()
        code = data.get('code')
        redirect_uri = data.get('redirect_uri')
        
        logging.info('--- API REQUEST RECEIVED ---')
        logging.info(f'Request data: {data}')
        
        # Step 1: Exchange authorization code for access token
        token_response = requests.post('https://id.twitch.tv/oauth2/token', {
            'client_id': TWITCH_CLIENT_ID,
            'client_secret': TWITCH_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri
        })
        
        if token_response.status_code != 200:
            raise Exception(f"Token exchange failed: {token_response.text}")
        
        token_data = token_response.json()
        access_token = token_data['access_token']
        logging.info('Got access token for user')
        
        # Step 2: Get user information
        user_response = requests.get('https://api.twitch.tv/helix/users', headers={
            'Authorization': f'Bearer {access_token}',
            'Client-Id': TWITCH_CLIENT_ID
        })
        
        if user_response.status_code != 200:
            raise Exception(f"User info request failed: {user_response.text}")
        
        user_data = user_response.json()['data'][0]
        logging.info(f'User data: {user_data["display_name"]} ({user_data["login"]})')
        
        # Step 3: Add channel to join list
        channel_name = user_data['login']
        add_channel_to_join_list(channel_name)
        
        return jsonify({
            'success': True,
            'message': 'Bot successfully added to channel',
            'channel': user_data['display_name'],
            'user_id': user_data['id']
        })
        
    except Exception as error:
        logging.error(f'Authorization error: {error}')
        return jsonify({
            'success': False,
            'error': 'Failed to process authorization',
            'details': str(error)
        }), 500

@flask_app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'OK', 'message': 'Meow Bot Auth API is running'})

def add_channel_to_join_list(channel_name):
    """Add channel to the join list file"""
    file_path = './channels_to_join.txt'
    logging.info('--- ATTEMPTING TO WRITE TO FILE ---')
    logging.info(f'Channel name: {channel_name}')
    logging.info(f'File path: {file_path}')
    
    try:
        channels = []
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                channels = [line.strip() for line in f if line.strip()]
            logging.info(f'Existing channels in file: {channels}')
        else:
            logging.info('File does not exist, will create new one')
        
        if channel_name not in channels:
            with open(file_path, 'a') as f:
                f.write(channel_name + '\n')
            logging.info(f'Successfully added channel to join list: {channel_name}')
        else:
            logging.info(f'Channel already in join list: {channel_name}')
    except Exception as err:
        logging.error(f'Error writing channel to file: {err}')

def run_flask_app():
    """Run Flask app in a separate thread"""
    flask_app.run(host='0.0.0.0', port=3000, debug=False, use_reloader=False)

class MeowDatabase:
    """Handle all database operations for meow counting"""
    
    def __init__(self, db_path: str = "meow_counts.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize optimized database tables"""
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                # Enable WAL mode for better concurrent access
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                
                cursor = conn.cursor()
            
                # Table for tracking meows per user per channel
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_meows (
                        user_id TEXT,
                        channel TEXT,
                        meow_count INTEGER DEFAULT 0,
                        first_meow_date TEXT,
                        last_meow_date TEXT,
                        PRIMARY KEY (user_id, channel)
                    )
                """)
                
                # Optimized channel settings (no payment columns)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS channel_settings (
                        channel TEXT PRIMARY KEY,
                        global_access BOOLEAN DEFAULT 0,
                        bot_enabled BOOLEAN DEFAULT 1,
                        join_approved BOOLEAN DEFAULT 0,
                        setup_date TEXT
                    )
                """)
                
                # Auto-fix database schema - add missing columns if they don't exist
                self._auto_migrate_schema(cursor)
                
                # Table for tracking all-time meows per streamer
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS streamer_totals (
                        channel TEXT PRIMARY KEY,
                        total_meows INTEGER DEFAULT 0,
                        first_meow_date TEXT,
                        last_meow_date TEXT
                    )
                """)
                
                # User global stats for cross-channel tracking
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_global_stats (
                        user_id TEXT PRIMARY KEY,
                        total_meows INTEGER DEFAULT 0,
                        channels_count INTEGER DEFAULT 0,
                        first_meow_date TEXT,
                        last_meow_date TEXT,
                        last_updated TEXT
                    )
                """)
                
                # Performance indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_meows_channel_count 
                    ON user_meows(channel, meow_count DESC)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_meows_user_channel 
                    ON user_meows(user_id, channel)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_streamer_totals_meows 
                    ON streamer_totals(total_meows DESC)
                """)
                
                conn.commit()
                logging.info("Optimized database initialized successfully")
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
            raise
    
    def _auto_migrate_schema(self, cursor):
        """Auto-migrate database schema to fix column mismatches"""
        try:
            # Get current columns in channel_settings
            cursor.execute("PRAGMA table_info(channel_settings)")
            columns = cursor.fetchall()
            current_columns = [col[1] for col in columns]
            
            # Add missing columns
            if 'join_approved' not in current_columns:
                cursor.execute("ALTER TABLE channel_settings ADD COLUMN join_approved BOOLEAN DEFAULT 0")
                logging.info("✅ Auto-migration: Added join_approved column")
            
            if 'global_access' not in current_columns:
                cursor.execute("ALTER TABLE channel_settings ADD COLUMN global_access BOOLEAN DEFAULT 0")
                logging.info("✅ Auto-migration: Added global_access column")
            
            # Migrate existing data and mark active channels as approved
            cursor.execute("""
                INSERT OR IGNORE INTO channel_settings (channel, join_approved, global_access)
                SELECT DISTINCT channel, 1, 1 
                FROM streamer_totals 
                WHERE total_meows > 0
            """)
            
            # Update existing channels to be approved if they have meow data
            cursor.execute("""
                UPDATE channel_settings 
                SET join_approved = 1, global_access = 1
                WHERE channel IN (
                    SELECT DISTINCT channel FROM streamer_totals WHERE total_meows > 0
                )
            """)
            
            # If global_leaderboard_opt_in exists, copy it to global_access
            if 'global_leaderboard_opt_in' in current_columns:
                cursor.execute("""
                    UPDATE channel_settings 
                    SET global_access = 1
                    WHERE global_leaderboard_opt_in = 1
                """)
                logging.info("✅ Auto-migration: Migrated global_leaderboard_opt_in data")
            
            # Count migrated channels
            cursor.execute("SELECT COUNT(*) FROM channel_settings WHERE join_approved = 1")
            approved_count = cursor.fetchone()[0]
            logging.info(f"✅ Auto-migration: {approved_count} channels marked as approved for rejoining")
            
        except Exception as e:
            logging.warning(f"Auto-migration warning: {e}")
    
    
    def add_meow(self, user_id: str, channel: str, count: int = 1) -> Tuple[int, int, int]:
        """
        Add meow(s) for a user in a channel
        Args:
            user_id: The user who meowed
            channel: The channel where they meowed
            count: Number of meows to add (default 1)
        Returns: (user_total, stream_total, streamer_total)
        """
        current_time = datetime.now().isoformat()
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Update user meows
            cursor.execute("""
                INSERT INTO user_meows (user_id, channel, meow_count, first_meow_date, last_meow_date)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, channel) DO UPDATE SET
                    meow_count = meow_count + ?,
                    last_meow_date = ?
            """, (user_id, channel, count, current_time, current_time, count, current_time))
            
            # Update streamer totals
            cursor.execute("""
                INSERT INTO streamer_totals (channel, total_meows, first_meow_date, last_meow_date)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(channel) DO UPDATE SET
                    total_meows = total_meows + ?,
                    last_meow_date = ?
            """, (channel, count, current_time, current_time, count, current_time))
            
            # Get current counts with error handling
            cursor.execute("SELECT meow_count FROM user_meows WHERE user_id = ? AND channel = ?", 
                         (user_id, channel))
            result = cursor.fetchone()
            user_total = result[0] if result else 0
            
            cursor.execute("SELECT total_meows FROM streamer_totals WHERE channel = ?", (channel,))
            result = cursor.fetchone()
            streamer_total = result[0] if result else 0
            
            # For stream_total, we'll use today's accumulated total from streamer_totals 
            # (since we removed the stream_meows table)
            stream_total = streamer_total
            
            conn.commit()
        
        # Update user global stats
        self.update_user_global_stats(user_id, count)
        
        return user_total, stream_total, streamer_total
    
    def update_user_global_stats(self, user_id: str, count: int = 1):
        """Update global stats for a user across all channels"""
        current_time = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Update or insert user global stats
            cursor.execute("""
                INSERT INTO user_global_stats (user_id, total_meows, channels_count, first_meow_date, last_meow_date, last_updated)
                VALUES (?, ?, 1, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    total_meows = total_meows + ?,
                    last_meow_date = ?,
                    last_updated = ?
            """, (user_id, count, current_time, current_time, current_time, count, current_time, current_time))
            
            # Update channels count
            cursor.execute("""
                UPDATE user_global_stats 
                SET channels_count = (
                    SELECT COUNT(DISTINCT channel) 
                    FROM user_meows 
                    WHERE user_id = ?
                )
                WHERE user_id = ?
            """, (user_id, user_id))
            
            conn.commit()
    
    def get_user_meows(self, user_id: str, channel: str) -> int:
        """Get total meows for a user in a specific channel"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT meow_count FROM user_meows WHERE user_id = ? AND channel = ?", 
                         (user_id, channel))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_stream_meows(self, channel: str) -> int:
        """Get total meows for a streamer (all time)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT total_meows FROM streamer_totals WHERE channel = ?", (channel,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_streamer_total_meows(self, channel: str) -> int:
        """Get all-time total meows for a streamer"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT total_meows FROM streamer_totals WHERE channel = ?", (channel,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_channel_leaderboard(self, channel: str, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top meowers in a specific channel (all time)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, meow_count 
                FROM user_meows 
                WHERE channel = ? 
                ORDER BY meow_count DESC 
                LIMIT ?
            """, (channel, limit))
            return cursor.fetchall()
    
    def get_global_leaderboard(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get global leaderboard of streamers (channels with global access)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Default channels that always have global access
            default_channels = ['meowcounterbot', 'snorlaxbuffet']
            
            # Try with new column name first, then fallback to old name
            try:
                cursor.execute("""
                    SELECT st.channel, st.total_meows 
                    FROM streamer_totals st
                    LEFT JOIN channel_settings cs ON st.channel = cs.channel
                    WHERE (cs.global_access = 1) 
                       OR (st.channel IN (?, ?))
                    ORDER BY st.total_meows DESC
                    LIMIT ?
                """, (*default_channels, limit))
                return cursor.fetchall()
            except sqlite3.OperationalError:
                # Fallback to old column name
                cursor.execute("""
                    SELECT st.channel, st.total_meows 
                    FROM streamer_totals st
                    LEFT JOIN channel_settings cs ON st.channel = cs.channel
                    WHERE (cs.global_leaderboard_opt_in = 1) 
                       OR (st.channel IN (?, ?))
                    ORDER BY st.total_meows DESC
                    LIMIT ?
                """, (*default_channels, limit))
                return cursor.fetchall()
    
    def approve_channel_join(self, channel: str):
        """Approve bot to join a channel"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO channel_settings (channel, join_approved)
                VALUES (?, 1)
                ON CONFLICT(channel) DO UPDATE SET join_approved = 1
            """, (channel,))
            conn.commit()
    
    def is_channel_approved(self, channel: str) -> bool:
        """Check if channel has approved bot joining"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT join_approved FROM channel_settings WHERE channel = ?", (channel,))
            result = cursor.fetchone()
            return bool(result[0]) if result else False
    
    def has_global_access(self, channel: str) -> bool:
        """Check if channel has opted into global leaderboard"""
        # Default channels always have access
        default_channels = ['meowcounterbot', 'snorlaxbuffet']
        if channel.lower() in default_channels:
            return True
            
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Try both column names for backward compatibility
            try:
                cursor.execute("""
                    SELECT global_access FROM channel_settings WHERE channel = ?
                """, (channel,))
                result = cursor.fetchone()
                if result and result[0]:
                    return True
            except sqlite3.OperationalError:
                pass
            
            # Fallback to old column name
            try:
                cursor.execute("""
                    SELECT global_leaderboard_opt_in FROM channel_settings WHERE channel = ?
                """, (channel,))
                result = cursor.fetchone()
                if result and result[0]:
                    return True
            except sqlite3.OperationalError:
                pass
            
            return False
    
    def opt_into_global(self, channel: str):
        """Opt a channel into global leaderboard"""
        current_time = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Use the correct column name (global_access)
            cursor.execute("""
                INSERT OR REPLACE INTO channel_settings (channel, global_access)
                VALUES (?, 1)
            """, (channel,))
            
            conn.commit()
            logging.info(f"Channel {channel} opted into global leaderboard")


class MeowBot(commands.Bot):
    def start_channel_watcher(self, file_path='./channels_to_join.txt', interval=60):
        def watcher():
            while True:
                try:
                    # Check for new channels from OAuth file
                    if os.path.exists(file_path):
                        with open(file_path, 'r') as f:
                            channels = [line.strip() for line in f if line.strip()]
                        
                        if channels:
                            logging.info(f"Found {len(channels)} channels in join file: {channels}")
                            
                        for channel in channels:
                            if channel not in [c.name for c in self.connected_channels]:
                                asyncio.run_coroutine_threadsafe(self.join_new_channel(channel), self.loop)
                                logging.info(f"Joined channel from file: {channel}")
                                
                                # Add to database for persistence
                                try:
                                    with sqlite3.connect(self.db.db_path) as conn:
                                        cursor = conn.cursor()
                                        cursor.execute("""
                                            INSERT OR REPLACE INTO channel_settings 
                                            (channel, join_approved, global_access) 
                                            VALUES (?, 1, 1)
                                        """, (channel,))
                                        conn.commit()
                                        logging.info(f'Added {channel} to database for persistence')
                                except Exception as db_error:
                                    logging.warning(f'Could not add {channel} to database: {db_error}')
                        
                        # Clear the file after processing all channels
                        if channels:
                            open(file_path, 'w').close()
                            logging.info(f"Cleared {len(channels)} channels from join file")
                            
                    time.sleep(interval)
                except Exception as e:
                    logging.error(f"Channel watcher error: {e}")
                    time.sleep(interval)
        thread = threading.Thread(target=watcher, daemon=True)
        thread.start()
    
    def load_approved_channels_from_db(self):
        """Load all approved channels from database and join them"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Get channels from channel_settings with flexible column checking
                approved_channels = []
                try:
                    cursor.execute("""
                        SELECT channel FROM channel_settings 
                        WHERE join_approved = 1
                    """)
                    approved_channels = [row[0] for row in cursor.fetchall()]
                    logging.info(f"Found {len(approved_channels)} approved channels in channel_settings")
                except sqlite3.OperationalError as e:
                    logging.info(f"join_approved column not found: {e}")
                
                # Try to get channels with global access (check both column names)
                try:
                    cursor.execute("""
                        SELECT channel FROM channel_settings 
                        WHERE global_access = 1
                    """)
                    global_channels = [row[0] for row in cursor.fetchall()]
                    approved_channels.extend(global_channels)
                    logging.info(f"Found {len(global_channels)} global access channels")
                except sqlite3.OperationalError:
                    # Try old column name
                    try:
                        cursor.execute("""
                            SELECT channel FROM channel_settings 
                            WHERE global_leaderboard_opt_in = 1
                        """)
                        global_channels = [row[0] for row in cursor.fetchall()]
                        approved_channels.extend(global_channels)
                        logging.info(f"Found {len(global_channels)} global access channels (legacy column)")
                    except sqlite3.OperationalError as e:
                        logging.info(f"No global access columns found: {e}")
                
                # Get ALL channels that have meow data (most reliable method)
                cursor.execute("""
                    SELECT DISTINCT channel FROM streamer_totals 
                    WHERE total_meows > 0
                """)
                active_channels = [row[0] for row in cursor.fetchall()]
                logging.info(f"Found {len(active_channels)} channels with meow data: {active_channels}")
                
                # Combine and deduplicate
                all_channels = list(set(approved_channels + active_channels))
                logging.info(f"Total {len(all_channels)} channels to rejoin from database: {all_channels}")
                
                return all_channels
        except Exception as e:
            logging.error(f"Error loading channels from database: {e}")
            return []
    
    async def join_approved_channels(self):
        """Join all previously approved channels from database"""
        channels_to_join = self.load_approved_channels_from_db()
        current_channels = [c.name for c in self.connected_channels]
        
        for channel in channels_to_join:
            if channel not in current_channels:
                try:
                    await self.join_new_channel(channel)
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(1)
                except Exception as e:
                    logging.error(f"Failed to rejoin channel {channel}: {e}")
    
    """Main bot class"""
    
    def __init__(self, token: str, prefix: str = "!", initial_channels: List[str] = None):
        # Use only ! prefix to avoid conflicts with Twitch native commands
        super().__init__(token=token, prefix=prefix, initial_channels=initial_channels or [])
        self.db = MeowDatabase()
        self.meow_pattern = re.compile(r'meow', re.IGNORECASE)
        self.rate_limiter = {}  # Track command usage per user
        self.max_channels = 100  # Twitch limit for verified bots
    
    def _count_overlapping_meows(self, text: str) -> int:
        """Count overlapping occurrences of 'meow' in text"""
        text_lower = text.lower()
        count = 0
        start = 0
        while True:
            pos = text_lower.find('meow', start)
            if pos == -1:
                break
            count += 1
            start = pos + 1  # Move by 1 to catch overlapping matches
        return count
    
    async def join_new_channel(self, channel_name: str):
        """Dynamically join a new channel"""
        try:
            await self.join_channels([channel_name])
            logging.info(f"Successfully joined new channel: {channel_name}")
            return True
        except Exception as e:
            logging.error(f"Failed to join channel {channel_name}: {e}")
            return False
    
    def start_railway_polling(self):
        """Start background polling of Railway API for new OAuth authorizations"""
        def poll_railway():
            processed_channels = set()  # Track channels we've already processed
            
            # Enhanced startup connection test
            railway_url = os.getenv('RAILWAY_API_URL', 'https://oauthmeow-production.up.railway.app')
            
            logging.info("=" * 60)
            logging.info("🚀 TESTING RAILWAY CONNECTION ON STARTUP")
            logging.info("=" * 60)
            logging.info(f"Railway URL: {railway_url}")
            
            # Test Railway connection on startup
            try:
                logging.info("📡 Testing Railway health endpoint...")
                health_response = requests.get(f'{railway_url}/api/health', timeout=10)
                if health_response.status_code == 200:
                    health_data = health_response.json()
                    logging.info("✅ Railway health check: SUCCESS")
                    logging.info(f"   Status: {health_data.get('status', 'Unknown')}")
                    logging.info(f"   Message: {health_data.get('message', 'No message')}")
                    logging.info(f"   Version: {health_data.get('version', 'Unknown')}")
                else:
                    logging.error(f"❌ Railway health check failed: {health_response.status_code}")
                    logging.error(f"   Response: {health_response.text}")
            except Exception as e:
                logging.error(f"🔥 CRITICAL: Cannot connect to Railway server!")
                logging.error(f"   Error: {e}")
                logging.error(f"   URL: {railway_url}")
                logging.error("   Bot will continue but OAuth won't work!")
            
            # Test pending channels endpoint
            try:
                logging.info("📡 Testing Railway pending-channels endpoint...")
                test_response = requests.get(f'{railway_url}/api/pending-channels', timeout=10)
                if test_response.status_code == 200:
                    test_data = test_response.json()
                    logging.info("✅ Railway pending-channels: SUCCESS")
                    logging.info(f"   Current pending channels: {len(test_data.get('channels', []))}")
                else:
                    logging.error(f"❌ Railway pending-channels failed: {test_response.status_code}")
            except Exception as e:
                logging.error(f"❌ Railway pending-channels test failed: {e}")
            
            logging.info("=" * 60)
            logging.info("🔄 STARTING RAILWAY POLLING LOOP (30 second intervals)")
            logging.info("=" * 60)
            
            while True:
                try:
                    # Poll Railway API for pending channels
                    response = requests.get(f'{railway_url}/api/pending-channels', timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        channels = data.get('channels', [])
                        
                        new_channels = 0
                        for channel_info in channels:
                            channel_name = channel_info.get('channel', '').lower()
                            display_name = channel_info.get('display_name', channel_name)
                            
                            # Skip if we've already processed this channel in this session
                            if channel_name in processed_channels:
                                continue
                                
                            # Skip if already connected
                            if channel_name in [ch.name for ch in self.connected_channels]:
                                processed_channels.add(channel_name)
                                logging.info(f'Skipping {channel_name} - already connected')
                                continue
                            
                            if channel_name:
                                # Mark as processed before attempting to join
                                processed_channels.add(channel_name)
                                
                                # Use asyncio to join the channel from the background thread
                                asyncio.run_coroutine_threadsafe(
                                    self.join_new_channel(channel_name), 
                                    self.loop
                                )
                                logging.info(f'Joined new channel from Railway OAuth: {display_name} ({channel_name})')
                                new_channels += 1
                                
                                # Add to database for persistence
                                try:
                                    with sqlite3.connect(self.db.db_path) as conn:
                                        cursor = conn.cursor()
                                        # Add to channel_settings with correct column names based on existing schema
                                        cursor.execute("""
                                            INSERT OR REPLACE INTO channel_settings 
                                            (channel, join_approved, global_access) 
                                            VALUES (?, 1, 1)
                                        """, (channel_name,))
                                        conn.commit()
                                        logging.info(f'Added {channel_name} to database for persistence')
                                except Exception as db_error:
                                    logging.warning(f'Could not add {channel_name} to database: {db_error}')
                        
                        if new_channels > 0:
                            logging.info(f"Railway API: Processed {new_channels} new channels")
                    else:
                        logging.warning(f'Railway API returned status {response.status_code}: {response.text}')
                    
                    time.sleep(30)  # Poll every 30 seconds
                    
                except requests.RequestException as e:
                    logging.warning(f'Could not poll Railway API: {e}')
                    time.sleep(30)  # Wait longer on network errors
                except Exception as e:
                    logging.error(f'Railway polling error: {e}')
                    time.sleep(30)
        
        # Start the polling thread
        polling_thread = threading.Thread(target=poll_railway, daemon=True)
        polling_thread.start()
        logging.info("Railway API polling started - checking for new OAuth authorizations every 30 seconds")
    
    async def event_ready(self):
        """Called when bot is ready"""
        logging.info(f'Bot {self.nick} is ready!')
        logging.info(f'Connected to initial channels: {[channel.name for channel in self.connected_channels]}')
        
        # Join all previously approved channels from database
        logging.info("Loading and joining approved channels from database...")
        await self.join_approved_channels()
        
        # Start Railway API polling for new OAuth authorizations
        self.start_railway_polling()
        
        # Log comprehensive channel summary
        all_channels = [channel.name for channel in self.connected_channels]
        total_channels = len(all_channels)
        
        logging.info("="*60)
        logging.info(f"🐱 MEOW BOT READY - Connected to {total_channels} channels:")
        logging.info("="*60)
        
        for i, channel in enumerate(sorted(all_channels), 1):
            logging.info(f"  {i:2d}. {channel}")
        
        logging.info("="*60)
        logging.info(f"✅ Bot is now monitoring {total_channels} stream channels for meows!")
        logging.info("="*60)
    
    async def event_error(self, error):
        """Handle connection errors"""
        logging.error(f'Bot error: {error}')
    
    async def event_channel_joined(self, channel):
        """Log when joining channels"""
        logging.info(f'Joined channel: {channel.name}')
    
    async def event_channel_join_failure(self, channel):
        """Handle failed channel joins"""
        logging.error(f'Failed to join channel: {channel}')
    
    async def event_command_error(self, ctx, error):
        """Handle command errors"""
        logging.error(f'Command error in {ctx.command}: {error}')
    
    async def event_message(self, message):
        """Handle incoming messages"""
        # Ignore messages from the bot itself - multiple checks
        if message.echo:
            return
        
        # Also ignore messages from the bot's own username
        if message.author and message.author.name.lower() == 'meowcounterbot':
            return
        
        try:
            # Check for meows in the message - count overlapping occurrences
            meow_count = self._count_overlapping_meows(message.content)
            if meow_count > 0:
                user_total, stream_total, streamer_total = self.db.add_meow(
                    message.author.name.lower(), 
                    message.channel.name.lower(),
                    meow_count  # Pass the actual count
                )
                
                # Rate limit responses (max 1 per 5 seconds per channel)
                channel_key = message.channel.name.lower()
                current_time = datetime.now().timestamp()
                
                if (channel_key not in self.rate_limiter or 
                    current_time - self.rate_limiter[channel_key] > 5):
                    try:
                        # More concise response
                        if meow_count > 1:
                            response = f"🐱 +{meow_count} meows! Stream total: {stream_total}"
                        else:
                            response = f"🐱 Stream meows: {stream_total}"
                        await message.channel.send(response)
                        self.rate_limiter[channel_key] = current_time
                    except Exception as send_error:
                        logging.error(f"Failed to send message to {message.channel.name}: {send_error}")
                
                logging.info(f"{meow_count} meow(s) detected from {message.author.name} in {message.channel.name}. Stream total: {stream_total}")
        
        except Exception as e:
            logging.error(f"Error processing message: {e}")
        
        # Handle commands with debugging
        if message.content.startswith('!'):
            logging.info(f"Command detected: '{message.content}' from {message.author.name}")
        await self.handle_commands(message)
    
    @commands.command(name='meow')
    async def user_meow_count(self, ctx):
        """Show user's total meow count (all time) in this channel"""
        user_meows = self.db.get_user_meows(ctx.author.name.lower(), ctx.channel.name.lower())
        await ctx.send(f"🐱 {ctx.author.name}: {user_meows} total meows in {ctx.channel.name}!")
    
    @commands.command(name='top')
    async def channel_leaderboard(self, ctx):
        """Show top meowers of all time in this channel"""
        leaderboard = self.db.get_channel_leaderboard(ctx.channel.name.lower(), 5)
        if not leaderboard:
            await ctx.send("🐱 No meows recorded in this channel yet!")
            return
        
        response = f"🏆 Top Meowers in {ctx.channel.name} (All Time):\n"
        for i, (user, meows) in enumerate(leaderboard, 1):
            response += f"{i}. {user}: {meows} meows\n"
        
        await ctx.send(response)
    
    @commands.command(name='global')
    async def global_leaderboard(self, ctx):
        """Show global leaderboard of streamers (opt-in feature)"""
        # Check if current channel has opted into global access
        if not self.db.has_global_access(ctx.channel.name.lower()):
            await ctx.send("🐱 Global leaderboard is opt-in only! Use !optinglobal to join the global leaderboard!")
            return
        
        leaderboard = self.db.get_global_leaderboard(5)
        if not leaderboard:
            await ctx.send("🐱 No streamers have opted into the global leaderboard yet!")
            return
        
        response = "🏆 Global Meow Leaderboard (All Time):\n"
        for i, (channel, meows) in enumerate(leaderboard, 1):
            response += f"{i}. {channel}: {meows} total meows\n"
        
        await ctx.send(response)
    
    @commands.command(name='requestbot')
    async def request_bot(self, ctx):
        """Direct users to the OAuth website for bot setup"""
        website_url = os.getenv('WEBSITE_URL', 'https://fireflydesigns.me/')
        
        # If it's the broadcaster in their own channel, they can still get instant setup
        if ctx.author.is_broadcaster:
            try:
                await self.join_new_channel(ctx.channel.name.lower())
                await ctx.send(f"🐱 ✅ Bot added to {ctx.channel.name}! Free meow counting now active! For advanced features, visit: {website_url}")
                logging.info(f"Broadcaster {ctx.author.name} approved bot for their channel: {ctx.channel.name}")
                return
            except Exception as e:
                await ctx.send(f"🐱 Error adding bot. Please try the OAuth setup at: {website_url}")
                logging.error(f"Failed to join {ctx.channel.name}: {e}")
                return
        
        # For everyone else, direct them to the website
        await ctx.send(f"🐱 Want Meow Bot in your channel? Visit {website_url} for easy OAuth setup! 🚀")
        logging.info(f"User {ctx.author.name} was directed to OAuth website for bot setup")
    
    @commands.command(name='optinglobal')
    async def opt_in_global(self, ctx):
        """Opt into global leaderboard (broadcaster only)"""
        if not ctx.author.is_broadcaster:
            await ctx.send("🐱 Only the broadcaster can opt their channel into the global leaderboard!")
            return
        
        # Opt the channel into global leaderboard
        self.db.opt_into_global(ctx.channel.name.lower())
        await ctx.send(f"🐱 ✅ {ctx.channel.name} has opted into the global leaderboard! Use !global to see rankings!")
        logging.info(f"Channel {ctx.channel.name} opted into global leaderboard")

    @commands.command(name='botinfo')
    async def bot_info(self, ctx):
        """Show bot creator information"""
        website_url = os.getenv('WEBSITE_URL', 'fireflydesigns.me')
        discord_id = os.getenv('DISCORD_ID', 'fireflyxserenity')
        await ctx.send(f"🐱 Meow Bot created by Firefly! Website: {website_url} | Discord: {discord_id}")

    @commands.command(name='help')
    async def meow_help(self, ctx):
        """Show available commands"""
        help_text = """🐱 Meow Bot Commands:
        !meow - Your total meow count in this channel
        !top - Top 5 meowers in this channel (all time)
        !global - Global leaderboard across all channels
        !optinglobal - Opt into global leaderboard (broadcaster only)
        !requestbot - Get bot setup instructions  
        !botinfo - Bot creator info
        !help - This help message"""
        
        await ctx.send(help_text)


def main():
    """Main function to run the bot"""
    
    # Enhanced startup logging with full environment diagnostics
    logging.info("=" * 70)
    logging.info("🤖 TWITCH MEOW BOT STARTING UP")
    logging.info("=" * 70)
    
    # Configuration - Load from environment
    BOT_TOKEN = os.getenv('TWITCH_BOT_TOKEN', 'your_bot_token_here')
    BOT_PREFIX = os.getenv('BOT_PREFIX', '!')
    INITIAL_CHANNELS = os.getenv('TWITCH_CHANNELS', '').split(',')
    RAILWAY_API_URL = os.getenv('RAILWAY_API_URL', 'https://oauthmeow-production.up.railway.app')
    
    # Environment variable diagnostics
    logging.info("🔧 ENVIRONMENT CONFIGURATION:")
    logging.info(f"   Bot Token: {'✅ CONFIGURED' if BOT_TOKEN != 'your_bot_token_here' else '❌ MISSING'}")
    logging.info(f"   Bot Prefix: {BOT_PREFIX}")
    logging.info(f"   Initial Channels: {INITIAL_CHANNELS if INITIAL_CHANNELS != [''] else '❌ NONE'}")
    logging.info(f"   Railway URL: {RAILWAY_API_URL}")
    logging.info(f"   Twitch Client ID: {TWITCH_CLIENT_ID}")
    logging.info(f"   Twitch Client Secret: {'✅ CONFIGURED' if TWITCH_CLIENT_SECRET else '❌ MISSING'}")
    
    # Critical environment variable checks
    if BOT_TOKEN == 'your_bot_token_here':
        logging.error("🔥 CRITICAL ERROR: TWITCH_BOT_TOKEN not configured!")
        logging.error("   Please set your TWITCH_BOT_TOKEN environment variable or edit the .env file")
        return
    
    if not INITIAL_CHANNELS or INITIAL_CHANNELS == ['']:
        logging.error("🔥 CRITICAL ERROR: TWITCH_CHANNELS not configured!")
        logging.error("   Please set your TWITCH_CHANNELS environment variable (comma-separated)")
        return
    
    if not TWITCH_CLIENT_SECRET:
        logging.error("🔥 CRITICAL ERROR: TWITCH_CLIENT_SECRET not configured!")
        logging.error("   OAuth functionality will not work!")
    
    logging.info("✅ Environment variables validated successfully")
    logging.info("=" * 70)
    
    # Start Flask server in a separate thread
    logging.info("🌐 Starting Flask OAuth server...")
    flask_thread = threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=3000, debug=False))
    flask_thread.daemon = True
    flask_thread.start()
    logging.info("✅ Flask OAuth server started on http://0.0.0.0:3000")
    
    # Create and run bot
    logging.info("🤖 Initializing MeowBot...")
    bot = MeowBot(
        token=BOT_TOKEN,
        prefix=BOT_PREFIX,
        initial_channels=INITIAL_CHANNELS
    )
    
    logging.info("📺 Starting channel watcher...")
    # Start watcher to join new channels automatically
    bot.start_channel_watcher()
    
    logging.info("=" * 70)
    logging.info("🚀 LAUNCHING BOT - Railway connection test will run shortly...")
    logging.info("=" * 70)
    
    try:
        bot.run()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Bot crashed: {e}")


if __name__ == "__main__":
    main()
