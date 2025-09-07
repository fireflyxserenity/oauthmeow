#!/usr/bin/env python3
"""
Test script to add a channel to database and verify persistence
"""
import sqlite3

def test_channel_persistence():
    try:
        conn = sqlite3.connect('meow_counts.db')
        cursor = conn.cursor()
        
        # Add test channel
        test_channel = "testchannel123"
        cursor.execute("""
            INSERT OR REPLACE INTO channel_settings 
            (channel, join_approved, global_leaderboard_opt_in) 
            VALUES (?, 1, 1)
        """, (test_channel,))
        conn.commit()
        print(f"✅ Added test channel: {test_channel}")
        
        # Verify it's there
        cursor.execute("SELECT * FROM channel_settings WHERE channel = ?", (test_channel,))
        result = cursor.fetchone()
        if result:
            print(f"✅ Channel found in database: {result}")
        else:
            print("❌ Channel not found in database")
        
        # Show all channels
        print("\n=== ALL CHANNELS IN DATABASE ===")
        cursor.execute("SELECT channel, join_approved, global_leaderboard_opt_in FROM channel_settings")
        channels = cursor.fetchall()
        for channel, approved, global_opt in channels:
            print(f"  {channel}: approved={approved}, global={global_opt}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_channel_persistence()
