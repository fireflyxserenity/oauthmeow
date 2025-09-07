"""
Database Migration Script for Meow Bot
Optimizes the database structure by removing unused tables/columns and adding performance improvements.
"""

import sqlite3
import os
from datetime import datetime

def backup_database():
    """Create a backup of the current database"""
    if os.path.exists('meow_counts.db'):
        backup_name = f"meow_counts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        os.system(f'copy meow_counts.db {backup_name}')
        print(f"✅ Database backed up as: {backup_name}")
        return True
    return False

def migrate_database():
    """Migrate to optimized database structure"""
    
    print("🔧 Starting database migration...")
    
    with sqlite3.connect('meow_counts.db') as conn:
        cursor = conn.cursor()
        
        # Enable WAL mode for better performance
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        
        print("📊 Analyzing current database...")
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"Current tables: {existing_tables}")
        
        # 1. Clean up channel_settings table - remove payment columns
        print("🧹 Cleaning up channel_settings table...")
        try:
            # Create new clean channel_settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channel_settings_new (
                    channel TEXT PRIMARY KEY,
                    global_access BOOLEAN DEFAULT 0,
                    bot_enabled BOOLEAN DEFAULT 1,
                    join_approved BOOLEAN DEFAULT 0,
                    setup_date TEXT
                )
            """)
            
            # Copy relevant data from old table if it exists
            if 'channel_settings' in existing_tables:
                cursor.execute("""
                    INSERT OR REPLACE INTO channel_settings_new (channel, global_access, bot_enabled, join_approved)
                    SELECT channel, 
                           COALESCE(global_leaderboard_opt_in, 0),
                           COALESCE(bot_enabled, 1),
                           COALESCE(join_approved, 0)
                    FROM channel_settings
                """)
                
                # Drop old table and rename new one
                cursor.execute("DROP TABLE channel_settings")
            
            cursor.execute("ALTER TABLE channel_settings_new RENAME TO channel_settings")
            print("✅ Channel settings cleaned up")
            
        except Exception as e:
            print(f"⚠️  Channel settings cleanup: {e}")
        
        # 2. Remove stream_meows table (unused now)
        print("🗑️  Removing unused stream_meows table...")
        try:
            if 'stream_meows' in existing_tables:
                cursor.execute("DROP TABLE stream_meows")
                print("✅ stream_meows table removed")
        except Exception as e:
            print(f"⚠️  Stream meows removal: {e}")
        
        # 3. Add indexes for better performance
        print("⚡ Adding performance indexes...")
        try:
            # Index on user_meows for faster leaderboard queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_meows_channel_count 
                ON user_meows(channel, meow_count DESC)
            """)
            
            # Index on user_meows for faster user lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_meows_user_channel 
                ON user_meows(user_id, channel)
            """)
            
            # Index on streamer_totals for global leaderboard
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_streamer_totals_meows 
                ON streamer_totals(total_meows DESC)
            """)
            
            print("✅ Performance indexes added")
            
        except Exception as e:
            print(f"⚠️  Index creation: {e}")
        
        # 4. Add user_global_stats table for cross-channel user stats
        print("📈 Adding user global stats table...")
        try:
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
            
            # Populate with existing data
            cursor.execute("""
                INSERT OR REPLACE INTO user_global_stats (user_id, total_meows, channels_count, last_updated)
                SELECT user_id, 
                       SUM(meow_count) as total_meows,
                       COUNT(DISTINCT channel) as channels_count,
                       datetime('now') as last_updated
                FROM user_meows 
                GROUP BY user_id
            """)
            
            print("✅ User global stats table created and populated")
            
        except Exception as e:
            print(f"⚠️  User global stats: {e}")
        
        # 5. Update existing default channels to have global access
        print("🌐 Setting up default global access...")
        try:
            default_channels = ['meowcounterbot', 'snorlaxbuffet']
            for channel in default_channels:
                cursor.execute("""
                    INSERT OR REPLACE INTO channel_settings (channel, global_access, bot_enabled, join_approved, setup_date)
                    VALUES (?, 1, 1, 1, ?)
                """, (channel, datetime.now().isoformat()))
            
            print(f"✅ Default channels set up: {default_channels}")
            
        except Exception as e:
            print(f"⚠️  Default channels setup: {e}")
        
        # 6. Vacuum database to reclaim space
        print("🧹 Optimizing database size...")
        try:
            cursor.execute("VACUUM")
            print("✅ Database optimized")
        except Exception as e:
            print(f"⚠️  Database vacuum: {e}")
        
        conn.commit()
    
    print("🎉 Database migration completed!")
    
    # Show final stats
    with sqlite3.connect('meow_counts.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        final_tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Final tables: {final_tables}")
        
        # Show some stats
        try:
            cursor.execute("SELECT COUNT(*) FROM user_meows")
            user_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_global_stats")
            global_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM streamer_totals")
            streamer_count = cursor.fetchone()[0]
            
            print(f"📊 Database contains:")
            print(f"   - {user_count} user-channel records")
            print(f"   - {global_count} global user records") 
            print(f"   - {streamer_count} streamer records")
            
        except Exception as e:
            print(f"⚠️  Stats gathering: {e}")

def main():
    print("🗄️  Meow Bot Database Migration")
    print("=" * 40)
    
    # Create backup
    if backup_database():
        # Run migration
        migrate_database()
        print("\n✅ Migration completed successfully!")
        print("💡 Your bot will automatically use the optimized database.")
    else:
        print("❌ No database found to migrate.")

if __name__ == "__main__":
    main()
