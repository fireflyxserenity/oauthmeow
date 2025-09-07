#!/usr/bin/env python3
"""
Quick database checker for meow bot
"""
import sqlite3

def check_database():
    try:
        conn = sqlite3.connect('meow_counts.db')
        cursor = conn.cursor()
        
        print("=== CHANNEL SETTINGS TABLE ===")
        cursor.execute("SELECT * FROM channel_settings")
        channels = cursor.fetchall()
        if channels:
            print("Channels in database:")
            for row in channels:
                print(f"  {row}")
        else:
            print("No channels found in channel_settings table")
        
        print("\n=== STREAMER TOTALS TABLE ===")
        cursor.execute("SELECT channel, total_meows FROM streamer_totals ORDER BY total_meows DESC LIMIT 10")
        streamers = cursor.fetchall()
        if streamers:
            print("Top channels by meow count:")
            for channel, meows in streamers:
                print(f"  {channel}: {meows} meows")
        else:
            print("No streamers found")
            
        print("\n=== TABLE STRUCTURE ===")
        cursor.execute("PRAGMA table_info(channel_settings)")
        columns = cursor.fetchall()
        print("channel_settings columns:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_database()
