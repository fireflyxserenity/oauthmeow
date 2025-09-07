"""
Twitch Meow Counter Bot - Simplified Version for Sparked Host

A Twitch IRC bot that counts "meow" messages in chat and provides various commands
to check meow statistics per user, per channel, and globally across streamers.

This version works with the separate OAuth server on Railway.
"""

import os
import re
import sqlite3
import asyncio
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from twitchio.ext import commands
from dotenv import load_dotenv
import logging
import threading
import time

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

# Bot Configuration
BOT_TOKEN = os.getenv('TWITCH_BOT_TOKEN', 'your_bot_token_here')
BOT_PREFIX = os.getenv('BOT_PREFIX', '!')
INITIAL_CHANNELS = [ch.strip() for ch in os.getenv('TWITCH_CHANNELS', '').split(',') if ch.strip()]
RAILWAY_API_URL = os.getenv('RAILWAY_API_URL', 'https://oauthmeow-production.up.railway.app')

class MeowDatabase:
    """Database handler for meow counting with comprehensive analytics"""
    
    def __init__(self, db_path: str = 'meow_counts.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with optimized schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main meow counts table with composite index
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meow_counts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                channel TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                first_meow TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_meow TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, channel)
            )
        ''')
        
        # Optimized indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_channel ON meow_counts(username, channel)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_channel_count ON meow_counts(channel, count DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_global_count ON meow_counts(count DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_meow ON meow_counts(last_meow DESC)')
        
        conn.commit()
        conn.close()
        logging.info("Optimized database initialized successfully")

    def add_meow(self, username: str, channel: str) -> int:
        """Add a meow for a user in a channel, return new count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO meow_counts (username, channel, count, last_meow) 
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(username, channel) 
            DO UPDATE SET 
                count = count + 1,
                last_meow = CURRENT_TIMESTAMP
        ''', (username, channel))
        
        # Get the updated count
        cursor.execute('SELECT count FROM meow_counts WHERE username = ? AND channel = ?', 
                      (username, channel))
        count = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        return count

    def get_user_stats(self, username: str, channel: str) -> Optional[Tuple[int, str, str]]:
        """Get user's meow stats for a specific channel"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT count, first_meow, last_meow 
            FROM meow_counts 
            WHERE username = ? AND channel = ?
        ''', (username, channel))
        result = cursor.fetchone()
        conn.close()
        return result

    def get_channel_leaderboard(self, channel: str, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top meowers for a specific channel"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, count 
            FROM meow_counts 
            WHERE channel = ? 
            ORDER BY count DESC 
            LIMIT ?
        ''', (channel, limit))
        results = cursor.fetchall()
        conn.close()
        return results

    def get_global_leaderboard(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get global top meowers across all channels"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, SUM(count) as total_meows
            FROM meow_counts 
            GROUP BY username 
            ORDER BY total_meows DESC 
            LIMIT ?
        ''', (limit,))
        results = cursor.fetchall()
        conn.close()
        return results

    def get_channel_stats(self, channel: str) -> Tuple[int, int, Optional[str]]:
        """Get channel statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total meows in channel
        cursor.execute('SELECT SUM(count) FROM meow_counts WHERE channel = ?', (channel,))
        total_meows = cursor.fetchone()[0] or 0
        
        # Unique meowers
        cursor.execute('SELECT COUNT(DISTINCT username) FROM meow_counts WHERE channel = ?', (channel,))
        unique_meowers = cursor.fetchone()[0] or 0
        
        # Top meower
        cursor.execute('''
            SELECT username FROM meow_counts 
            WHERE channel = ? 
            ORDER BY count DESC 
            LIMIT 1
        ''', (channel,))
        result = cursor.fetchone()
        top_meower = result[0] if result else None
        
        conn.close()
        return total_meows, unique_meowers, top_meower

class MeowBot(commands.Bot):
    def __init__(self, token: str, prefix: str, initial_channels: List[str]):
        super().__init__(token=token, prefix=prefix, initial_channels=initial_channels)
        self.db = MeowDatabase()
        self.meow_pattern = re.compile(r'\b(meow+|mrow+|mrrow+|meeeow+|miau+)\b', re.IGNORECASE)
        
    async def event_ready(self):
        logging.info(f'Bot {self.nick} is ready!')
        logging.info(f'Connected to channels: {[channel.name for channel in self.connected_channels]}')

    async def event_message(self, message):
        if message.echo:
            return
        
        # Count meows in the message
        meow_matches = self.meow_pattern.findall(message.content.lower())
        if meow_matches:
            channel_name = message.channel.name.lower()
            username = message.author.name.lower()
            
            # Add each meow found
            for _ in meow_matches:
                new_count = self.db.add_meow(username, channel_name)
            
            logging.info(f'Meow detected from {username} in #{channel_name} (Total: {new_count})')
            
            # Send automatic response for meows
            try:
                await message.channel.send(f"🐱 {message.author.name}: {new_count} total meows in {channel_name}!")
            except Exception as e:
                logging.error(f'Failed to send meow response: {e}')
        
        await self.handle_commands(message)

    @commands.command(name='meow')
    async def meow_stats(self, ctx):
        """Shows your total meow count (all time) in the current channel"""
        username = ctx.author.name.lower()
        channel = ctx.channel.name.lower()
        
        stats = self.db.get_user_stats(username, channel)
        if stats:
            count, first_meow, last_meow = stats
            await ctx.send(f"🐱 {ctx.author.name}: {count} total meows in {channel}!")
        else:
            await ctx.send(f"🐱 {ctx.author.name}: 0 total meows in {channel}! Type 'meow' to start counting!")

    @commands.command(name='top')
    async def top_meowers(self, ctx):
        """Shows the top 5 meowers of all time in the current channel"""
        channel = ctx.channel.name.lower()
        leaderboard = self.db.get_channel_leaderboard(channel, 5)
        
        if leaderboard:
            leaders = [f"{i+1}. {user} ({count})" for i, (user, count) in enumerate(leaderboard)]
            await ctx.send(f"🏆 Top 5 in #{channel}: " + " | ".join(leaders))
        else:
            await ctx.send("🐱 No meows recorded in this channel yet!")

    @commands.command(name='global')
    async def global_leaderboard(self, ctx):
        """Shows the global leaderboard of streamers across all channels"""
        leaderboard = self.db.get_global_leaderboard(5)
        
        if leaderboard:
            leaders = [f"{i+1}. {user} ({count})" for i, (user, count) in enumerate(leaderboard)]
            await ctx.send(f"🌍 Global Top 5: " + " | ".join(leaders))
        else:
            await ctx.send("🐱 No global meow data available!")

    @commands.command(name='requestbot')
    async def request_bot(self, ctx):
        """Provides instructions for adding the bot to a channel"""
        if ctx.author.name.lower() == ctx.channel.name.lower():
            # User is the broadcaster
            try:
                # Try to add the bot automatically if they're the broadcaster
                # This would need implementation based on your OAuth system
                await ctx.send(f"🐱 Want Meow Bot in your channel? Visit https://fireflydesigns.me/twitch.html for easy setup! 🚀")
            except Exception:
                await ctx.send(f"🐱 Error adding bot. Please try the setup at: https://fireflydesigns.me/twitch.html")
        else:
            # Regular user asking for bot
            await ctx.send(f"🐱 Want Meow Bot in your channel? Visit https://fireflydesigns.me/twitch.html for easy setup! 🚀")

    @commands.command(name='optinglobal')
    async def opt_global(self, ctx):
        """Opts the channel into the global leaderboard (broadcaster only)"""
        if ctx.author.name.lower() == ctx.channel.name.lower():
            # Only broadcaster can opt into global
            # For now, all channels are automatically opted in
            await ctx.send(f"🌍 #{ctx.channel.name} is already opted into the global leaderboard! Use !global to see it.")
        else:
            await ctx.send(f"🐱 Only the broadcaster can manage global leaderboard settings!")

    @commands.command(name='botinfo')
    async def bot_info(self, ctx):
        """Shows bot creator information and contact details"""
        await ctx.send(f"🐱 Meow Bot created by FireflyxSerenity | Original concept by SnorlaxBuffet | Visit: https://fireflydesigns.me")

    @commands.command(name='help')
    async def help_command(self, ctx):
        """Shows all available commands"""
        commands_list = [
            "!meow - Your meow count",
            "!top - Top 5 meowers", 
            "!global - Global leaderboard",
            "!requestbot - Add bot to channel",
            "!botinfo - Bot info",
            "!help - This message"
        ]
        await ctx.send(f"🐱 Commands: " + " | ".join(commands_list))

    def start_channel_watcher(self):
        """Start watching for new channels to join"""
        def watch_channels():
            while True:
                try:
                    # Method 1: Check file for local additions
                    if os.path.exists('./channels_to_join.txt'):
                        with open('./channels_to_join.txt', 'r') as f:
                            channels = [line.strip() for line in f.readlines() if line.strip()]
                        
                        if channels:
                            for channel in channels:
                                if channel and channel not in [ch.name for ch in self.connected_channels]:
                                    asyncio.run_coroutine_threadsafe(
                                        self.join_channels([channel]), 
                                        self.loop
                                    )
                                    logging.info(f'Joined new channel from file: {channel}')
                            
                            # Clear the file after processing
                            open('./channels_to_join.txt', 'w').close()
                    
                    # Method 2: Poll Railway API for OAuth additions
                    try:
                        response = requests.get(f'{RAILWAY_API_URL}/api/pending-channels', timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            for channel_info in data.get('channels', []):
                                channel_name = channel_info.get('channel', '').lower()
                                if channel_name and channel_name not in [ch.name for ch in self.connected_channels]:
                                    asyncio.run_coroutine_threadsafe(
                                        self.join_channels([channel_name]), 
                                        self.loop
                                    )
                                    logging.info(f'Joined new channel from OAuth: {channel_name} ({channel_info.get("display_name", "")})')
                    except requests.RequestException as e:
                        logging.warning(f'Could not poll Railway API: {e}')
                    except Exception as e:
                        logging.error(f'Railway polling error: {e}')
                    
                    time.sleep(10)  # Check every 10 seconds
                except Exception as e:
                    logging.error(f'Channel watcher error: {e}')
                    time.sleep(30)
        
        watcher_thread = threading.Thread(target=watch_channels)
        watcher_thread.daemon = True
        watcher_thread.start()
        logging.info("Channel watcher started (file + Railway API polling)")

def main():
    if BOT_TOKEN == 'your_bot_token_here':
        print("Please set your TWITCH_BOT_TOKEN environment variable or edit the .env file")
        return
    
    if not INITIAL_CHANNELS or INITIAL_CHANNELS == ['']:
        print("Please set your TWITCH_CHANNELS environment variable (comma-separated)")
        return
    
    # Create and run bot
    bot = MeowBot(
        token=BOT_TOKEN,
        prefix=BOT_PREFIX,
        initial_channels=INITIAL_CHANNELS
    )
    # Start watcher to join new channels automatically
    bot.start_channel_watcher()
    try:
        bot.run()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Bot crashed: {e}")

if __name__ == "__main__":
    main()
