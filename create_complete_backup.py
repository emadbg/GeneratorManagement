import psycopg2
import json

print("📦 Creating complete backup with table structure...")

# Connect to local database
conn = psycopg2.connect(
    host="localhost",
    database="generator_payments",
    user="postgres",
    password="Database2025",
    port="5432"
)

cursor = conn.cursor()

# Get table creation statements
cursor.execute("""
    SELECT tablename 
    FROM pg_tables 
    WHERE schemaname = 'public'
    ORDER BY tablename
""")

tables = [row[0] for row in cursor.fetchall()]

sql_content = []
sql_content.append("-- COMPLETE DATABASE BACKUP")
sql_content.append("-- Includes table structure and data")
sql_content.append("")

# 1. First, get table creation SQL
for table in tables:
    cursor.execute(f"""
        SELECT 'CREATE TABLE ' || table_name || ' (' || 
               string_agg(column_name || ' ' || data_type || 
                          CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END ||
                          CASE WHEN column_default IS NOT NULL THEN ' DEFAULT ' || column_default ELSE '' END, 
                          ', ') || 
               ');' as create_sql
        FROM information_schema.columns 
        WHERE table_name = '{table}'
        GROUP BY table_name
    """)
    
    create_sql = cursor.fetchone()
    if create_sql:
        sql_content.append(create_sql[0])
        sql_content.append("")
        
        # 2. Get data for this table
        cursor.execute(f"SELECT * FROM {table}")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        if rows:
            for row in rows:
                values = []
                for value in row:
                    if value is None:
                        values.append('NULL')
                    elif isinstance(value, bool):
                        values.append('TRUE' if value else 'FALSE')
                    elif isinstance(value, (int, float)):
                        values.append(str(value))
                    else:
                        value_str = str(value).replace("'", "''")
                        values.append(f"'{value_str}'")
                
                columns_str = ', '.join(columns)
                values_str = ', '.join(values)
                sql_content.append(f"INSERT INTO {table} ({columns_str}) VALUES ({values_str});")
            
            sql_content.append("")

cursor.close()
conn.close()

# Write to file
with open('complete_backup.sql', 'w', encoding='utf-8') as f:
    f.write('\n'.join(sql_content))

print(f"✅ Complete backup created: complete_backup.sql")
print(f"📊 Tables: {len(tables)}")