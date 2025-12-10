import json

print("📝 Creating backup.sql from database_export.json...")

# Load your exported data
with open('database_export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

sql_content = []
sql_content.append("-- Generator Payments Database Backup")
sql_content.append("-- Generated for Railway Migration")
sql_content.append("")

# Tables in correct order for foreign keys
tables_order = ['instances', 'app_settings', 'users', 'clients', 'payments']

for table in tables_order:
    if table in data and data[table]:
        print(f"  Processing {table}...")
        
        # Get column names from first row
        first_row = data[table][0]
        columns = list(first_row.keys())
        
        for row in data[table]:
            # Prepare values for SQL
            values = []
            for col in columns:
                value = row.get(col)
                
                if value is None:
                    values.append('NULL')
                elif isinstance(value, bool):
                    values.append('TRUE' if value else 'FALSE')
                elif isinstance(value, (int, float)):
                    values.append(str(value))
                else:
                    # Escape single quotes in strings
                    value_str = str(value).replace("'", "''")
                    values.append(f"'{value_str}'")
            
            columns_str = ', '.join(columns)
            values_str = ', '.join(values)
            
            sql_content.append(f"INSERT INTO {table} ({columns_str}) VALUES ({values_str});")
        
        sql_content.append("")

# Write to file
with open('backup.sql', 'w', encoding='utf-8') as f:
    f.write('\n'.join(sql_content))

print(f"✅ backup.sql created successfully!")
print(f"📊 Tables processed: {len(tables_order)}")