import psycopg2
from psycopg2.extras import RealDictCursor

print("🚀 Direct migration from local to Railway")

# Local database connection
local_conn = psycopg2.connect(
    host="localhost",
    database="generator_payments",
    user="postgres",
    password="Database2025",
    port="5432"
)

# Railway database connection - UPDATE THIS WITH YOUR URL!
railway_db_url = "postgresql://postgres:hBjHVtwjcKUsQIZjhlUREBNMFzTJFhsK@metro.proxy.rlwy.net:13826/railway"

railway_conn = psycopg2.connect(railway_db_url, sslmode='require')

local_cur = local_conn.cursor(cursor_factory=RealDictCursor)
railway_cur = railway_conn.cursor()

# Create tables on Railway first
print("1. Creating tables on Railway...")

create_tables_sql = """
-- Drop existing tables if they exist
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS clients CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS app_settings CASCADE;
DROP TABLE IF EXISTS instances CASCADE;

-- Create tables
CREATE TABLE instances (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    instance_key VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE app_settings (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    header_title VARCHAR(255) DEFAULT 'Default Title',
    receipt_header VARCHAR(255) DEFAULT 'Default Date',
    payment_id_start INTEGER DEFAULT 1000,
    currency_symbol VARCHAR(10) DEFAULT 'SAR',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(instance_id)
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    username VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(instance_id, username)
);

CREATE TABLE clients (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    name VARCHAR(255) NOT NULL,
    monthly_fee NUMERIC DEFAULT 0.00,
    prev_counter INTEGER DEFAULT 0,
    current_counter INTEGER DEFAULT 0,
    total_usage INTEGER DEFAULT 0,
    kilowatt_price NUMERIC DEFAULT 0.00,
    amount_usage NUMERIC DEFAULT 0.00,
    prev_balance NUMERIC DEFAULT 0.00,
    current_balance NUMERIC DEFAULT 0.00,
    payment_amt NUMERIC DEFAULT 0.00,
    new_balance NUMERIC DEFAULT 0.00,
    last_paid_by VARCHAR(100),
    pay_id VARCHAR(50),
    cust_id VARCHAR(50),
    phone VARCHAR(20),
    address TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES instances(id),
    payment_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    date_entered TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    username VARCHAR(100) NOT NULL,
    previous_balance_logged NUMERIC DEFAULT 0.00,
    total_due_before_payment NUMERIC DEFAULT 0.00,
    payment_amount NUMERIC NOT NULL,
    new_balance NUMERIC DEFAULT 0.00,
    customer_id VARCHAR(50),
    monthly_fee NUMERIC DEFAULT 0.00,
    previous_counter INTEGER DEFAULT 0,
    current_counter INTEGER DEFAULT 0,
    total_usage INTEGER DEFAULT 0,
    kilowatt_price NUMERIC DEFAULT 0.00,
    amount_usage NUMERIC DEFAULT 0.00,
    previous_balance_data NUMERIC DEFAULT 0.00,
    current_balance_data NUMERIC DEFAULT 0.00,
    is_first_payment BOOLEAN DEFAULT FALSE,
    duplicate_cleaned TEXT,
    receipt_printed BOOLEAN DEFAULT FALSE,
    receipt_printed_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(instance_id, payment_id)
);
"""

# Split and execute SQL commands
for sql in create_tables_sql.split(';'):
    if sql.strip():
        try:
            railway_cur.execute(sql)
        except Exception as e:
            print(f"   Warning: {e}")

railway_conn.commit()
print("   ✅ Tables created")

# Copy data table by table
print("\n2. Copying data...")

tables = ['instances', 'app_settings', 'users', 'clients', 'payments']

for table in tables:
    print(f"   Copying {table}...")
    
    # Get data from local
    local_cur.execute(f"SELECT * FROM {table}")
    rows = local_cur.fetchall()
    
    if rows:
        # Get column names
        columns = list(rows[0].keys())
        
        # Insert into Railway
        inserted = 0
        for row in rows:
            # Prepare values
            values = []
            for col in columns:
                value = row[col]
                values.append(value)
            
            # Build INSERT query
            cols_str = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(values))
            
            sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})"
            
            try:
                railway_cur.execute(sql, values)
                inserted += 1
            except Exception as e:
                print(f"     Warning on row {inserted+1}: {e}")
        
        railway_conn.commit()
        print(f"     ✅ {inserted} rows copied")
    else:
        print(f"     ⚠️ No data in {table}")

print("\n🎉 Migration completed successfully!")
print("✅ Database is ready on Railway")

local_cur.close()
railway_cur.close()
local_conn.close()
railway_conn.close()