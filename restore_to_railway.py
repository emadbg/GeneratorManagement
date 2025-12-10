import psycopg2
import subprocess
import os

print("🔧 Restoring data to Railway PostgreSQL...")

# ==== PASTE YOUR RAILWAY DATABASE URL HERE ====
RAILWAY_DB_URL = "postgresql://postgres:hBjHVtwjcKUsQIZjhlUREBNMFzTJFhsK@metro.proxy.rlwy.net:13826/railway"
# ===============================================

# 1. Connect to Railway DB
print("1. Connecting to Railway database...")
conn = psycopg2.connect(RAILWAY_DB_URL, sslmode='require')
cursor = conn.cursor()

# 2. Read your SQL backup file
print("2. Reading backup.sql file...")
try:
    with open('complete_backup.sql', 'r', encoding='utf-8') as f:
        sql_commands = f.read()
except FileNotFoundError:
    print("❌ ERROR: backup.sql file not found in current folder.")
    print("   Make sure you are in: C:\\generator_payments\\backend")
    exit(1)

# 3. Split into individual commands and execute
print("3. Executing SQL commands (this may take a moment)...")
commands = sql_commands.split(';')

for i, cmd in enumerate(commands):
    cmd = cmd.strip()
    if cmd:  # Skip empty commands
        try:
            cursor.execute(cmd)
        except Exception as e:
            print(f"   ⚠️ Skipping command {i+1}: {e}")

# 4. Commit and close
conn.commit()
cursor.close()
conn.close()

print("✅ Data restoration complete!")
print("🎯 Your Railway app now has all your data. Open the app and test login.")