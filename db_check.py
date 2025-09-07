import sqlite3

print('Connecting to database...')
conn = sqlite3.connect('meow_counts.db')
cursor = conn.cursor()

print('=== TABLES ===')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for t in tables:
    print(f'- {t[0]}')

print('\n=== CHANNEL_SETTINGS COLUMNS ===')
cursor.execute('PRAGMA table_info(channel_settings)')
columns = cursor.fetchall()
for col in columns:
    print(f'{col[1]} ({col[2]})')

print('\n=== SAMPLE DATA COUNTS ===')
cursor.execute('SELECT COUNT(*) FROM user_meows')
print(f'user_meows: {cursor.fetchone()[0]} records')

cursor.execute('SELECT COUNT(*) FROM streamer_totals') 
print(f'streamer_totals: {cursor.fetchone()[0]} records')

cursor.execute('SELECT COUNT(*) FROM channel_settings')
print(f'channel_settings: {cursor.fetchone()[0]} records')

print('\n=== SAMPLE CHANNELS ===')
cursor.execute('SELECT channel FROM channel_settings LIMIT 5')
channels = cursor.fetchall()
for ch in channels:
    print(f'- {ch[0]}')

conn.close()
print('Database check complete!')
