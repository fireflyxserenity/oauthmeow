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
        
        await self.handle_commands(message)

    @commands.command(name='meowstats')
    async def meow_stats(self, ctx):
        """Get user's meow statistics for this channel"""
        username = ctx.author.name.lower()
        channel = ctx.channel.name.lower()
        
        stats = self.db.get_user_stats(username, channel)
        if stats:
            count, first_meow, last_meow = stats
            await ctx.send(f"@{ctx.author.name} 🐱 You have meowed {count} times in this channel! First meow: {first_meow[:10]}")
        else:
            await ctx.send(f"@{ctx.author.name} 🐱 You haven't meowed in this channel yet! Type 'meow' to start counting!")

    @commands.command(name='topmew', aliases=['meowboard', 'meowleaders'])
    async def top_meowers(self, ctx):
        """Get channel leaderboard"""
        channel = ctx.channel.name.lower()
        leaderboard = self.db.get_channel_leaderboard(channel, 5)
        
        if leaderboard:
            leaders = [f"{i+1}. {user} ({count} meows)" for i, (user, count) in enumerate(leaderboard)]
            await ctx.send(f"🏆 Top Meowers in #{channel}: " + " | ".join(leaders))
        else:
            await ctx.send("🐱 No meows recorded in this channel yet!")

    @commands.command(name='globalmew', aliases=['globalmeow'])
    async def global_leaderboard(self, ctx):
        """Get global leaderboard across all channels"""
        leaderboard = self.db.get_global_leaderboard(5)
        
        if leaderboard:
            leaders = [f"{i+1}. {user} ({count} total)" for i, (user, count) in enumerate(leaderboard)]
            await ctx.send(f"🌍 Global Meow Leaders: " + " | ".join(leaders))
        else:
            await ctx.send("🐱 No global meow data available!")

    @commands.command(name='meowinfo')
    async def channel_info(self, ctx):
        """Get channel meow statistics"""
        channel = ctx.channel.name.lower()
        total_meows, unique_meowers, top_meower = self.db.get_channel_stats(channel)
        
        await ctx.send(f"📊 #{channel} Meow Stats: {total_meows} total meows from {unique_meowers} unique meowers. Top meower: {top_meower or 'None yet!'}")

    def start_channel_watcher(self):
        """Start watching for new channels to join"""
        def watch_channels():
            while True:
                try:
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
                                    logging.info(f'Joined new channel: {channel}')
                            
                            # Clear the file after processing
                            open('./channels_to_join.txt', 'w').close()
                    
                    time.sleep(10)  # Check every 10 seconds
                except Exception as e:
                    logging.error(f'Channel watcher error: {e}')
                    time.sleep(30)
        
        watcher_thread = threading.Thread(target=watch_channels)
        watcher_thread.daemon = True
        watcher_thread.start()
        logging.info("Channel watcher started")

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
