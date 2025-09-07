#!/usr/bin/env python3
"""
Quick Database Fix for Column Mismatch
This fixes the disconnect between old column names and new bot code
"""
import sqlite3

def fix_database_columns():
    """Fix column mismatches between database and bot code"""
    try:
        conn = sqlite3.connect('meow_counts.db')
        cursor = conn.cursor()
        
        print("=== CHECKING DATABASE STRUCTURE ===")
        cursor.execute("PRAGMA table_info(channel_settings)")
        columns = cursor.fetchall()
        current_columns = [col[1] for col in columns]
        print(f"Current columns: {current_columns}")
        
        # Add missing columns if needed
        if 'join_approved' not in current_columns:
            print("Adding join_approved column...")
            cursor.execute("ALTER TABLE channel_settings ADD COLUMN join_approved BOOLEAN DEFAULT 0")
            print("✅ Added join_approved column")
        
        if 'global_access' not in current_columns:
            print("Adding global_access column...")  
            cursor.execute("ALTER TABLE channel_settings ADD COLUMN global_access BOOLEAN DEFAULT 0")
            print("✅ Added global_access column")
        
        # Mark all channels with meow data as approved
        print("\n=== MARKING CHANNELS AS APPROVED ===")
        
        # First, add any missing channels from streamer_totals
        cursor.execute("""
            INSERT OR IGNORE INTO channel_settings (channel, join_approved, global_access)
            SELECT DISTINCT channel, 1, 1 
            FROM streamer_totals 
            WHERE total_meows > 0
        """)
        
        # Update existing channels to be approved
        cursor.execute("""
            UPDATE channel_settings 
            SET join_approved = 1, global_access = 1
            WHERE channel IN (
                SELECT DISTINCT channel FROM streamer_totals WHERE total_meows > 0
            )
        """)
        
        # Also copy from global_leaderboard_opt_in if it exists
        if 'global_leaderboard_opt_in' in current_columns:
            cursor.execute("""
                UPDATE channel_settings 
                SET global_access = 1
                WHERE global_leaderboard_opt_in = 1
            """)
            print("✅ Migrated global_leaderboard_opt_in data")
        
        conn.commit()
        
        # Show results
        print("\n=== RESULTS ===")
        cursor.execute("""
            SELECT channel, join_approved, global_access 
            FROM channel_settings 
            WHERE join_approved = 1
        """)
        approved_channels = cursor.fetchall()
        
        print(f"✅ {len(approved_channels)} channels now marked as approved:")
        for channel, approved, global_access in approved_channels:
            print(f"  - {channel}: approved={approved}, global={global_access}")
        
        conn.close()
        print(f"\n🎉 Database fixed! Your bot should now find {len(approved_channels)} channels to rejoin.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_database_columns()
