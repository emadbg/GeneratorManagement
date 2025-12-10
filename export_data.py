import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
from decimal import Decimal

def decimal_default(obj):
    """Convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def export_database():
    """Export all data from local database for migration to Railway"""
    
    print("📤 Exporting database for Railway migration...")
    
    # Connect to local database
    conn = psycopg2.connect(
        host="localhost",
        database="generator_payments",
        user="postgres",
        password="Database2025",
        port="5432"
    )
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    export_data = {}
    
    # List of tables to export (in correct order for foreign keys)
    tables = [
        'instances',
        'app_settings',
        'users',
        'clients',
        'payments',
        'audit_log',
        'import_logs'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"SELECT * FROM {table} ORDER BY id")
            rows = cursor.fetchall()
            
            # Convert each row to dictionary
            table_data = []
            for row in rows:
                row_dict = dict(row)
                table_data.append(row_dict)
            
            export_data[table] = table_data
            print(f"✅ {table}: {len(table_data)} records")
            
        except Exception as e:
            print(f"⚠️ Skipping {table}: {e}")
    
    # Save to JSON file with custom encoder
    with open('database_export.json', 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, default=decimal_default, ensure_ascii=False)
    
    print(f"\n🎯 Export completed!")
    print(f"📁 File saved: database_export.json")
    print(f"📊 Total records: {sum(len(v) for v in export_data.values())}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    export_database()