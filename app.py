from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime, timedelta
from functools import wraps
import bcrypt
import os
import psycopg2
import os
PORT = int(os.environ.get('PORT', 8000))
from psycopg2.extras import RealDictCursor


app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, supports_credentials=True)

def get_db():
    """
    Get PostgreSQL database connection.
    Returns: (connection, cursor) tuple
    """
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    print(f"DEBUG: DATABASE_URL = {DATABASE_URL[:50] if DATABASE_URL else 'NOT SET'}...")  # Debug line
    
    if DATABASE_URL:
        # Production (Railway)
        # IMPORTANT: Railway requires sslmode='require'
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        # Development (your local PC)
        conn = psycopg2.connect(
            host="localhost",
            database="generator_payments",
            user="postgres",
            password="Database2025",  # Your local password
            port="5432"
        )
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    return conn, cursor

# ====== CORS DECORATOR ======
def cors_headers(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'preflight'})
        else:
            response = f(*args, **kwargs)
            if isinstance(response, tuple):
                response, status = response
                response = jsonify(response)
                response.status_code = status
            else:
                response = jsonify(response)
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Max-Age', '86400')
        
        return response
    return decorated_function

# ====== SERVE HTML PAGES ======
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/mobile')
def serve_mobile():
    return send_from_directory('.', 'mobile.html')

@app.route('/simple')
def serve_simple():
    return send_from_directory('.', 'simple_login.html')

# ====== HEALTH CHECK ======
@app.route('/api/health', methods=['GET', 'OPTIONS'])
@cors_headers
def health_check():
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mobile_url": "http://192.168.1.27:8000",
        "local_url": "http://localhost:8000"
    }

# ====== SETTINGS ======
@app.route('/api/settings', methods=['GET', 'OPTIONS'])
@cors_headers
def get_app_settings():
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    try:
        conn, cursor = get_db()
        
        cursor.execute("SELECT header_title, receipt_header, payment_id_start FROM app_settings WHERE instance_id = 1")
        settings = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if settings:
            return {
                "headerTitle": settings['header_title'],
                "receiptHeader": settings['receipt_header'],
                "paymentIdStart": settings['payment_id_start']
            }
        else:
            return {
                "headerTitle": "مولدات بيصور H D A",
                "receiptHeader": datetime.now().strftime("%Y-%m-%d"),
                "paymentIdStart": 1000
            }
            
    except Exception as e:
        print(f"Settings error: {e}")
        return {
            "headerTitle": "Generator Payments",
            "receiptHeader": datetime.now().strftime("%Y-%m-%d"),
            "paymentIdStart": 1000
        }

# ====== AUTHENTICATION ======
@app.route('/api/auth/check', methods=['GET', 'OPTIONS'])
@cors_headers
def check_auth_enabled():
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    try:
        conn, cursor = get_db()
        cursor.execute("SELECT COUNT(*) as user_count FROM users")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return {"hasUsersSheet": result['user_count'] > 0}
    except Exception as e:
        print(f"Auth check error: {e}")
        return {"hasUsersSheet": False}

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
@cors_headers
def login():
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        print(f"Login attempt: username={username}")
        
        if not username or not password:
            return {
                "success": False,
                "error": "Username and password are required"
            }, 400
        
        conn, cursor = get_db()
        
        # Get user with password hash
        cursor.execute("""
            SELECT id, username, password_hash, full_name, is_admin, instance_id 
            FROM users 
            WHERE username = %s AND is_active = TRUE
        """, (username,))
        
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            print(f"User not found: {username}")
            return {
                "success": False,
                "error": "Invalid username or password"
            }
        
        # Verify password against bcrypt hash
        stored_hash = user['password_hash']
        print(f"Checking password for user: {username}")
        
        # Check if it's a bcrypt hash
        if stored_hash.startswith('$2b$'):
            # Compare with bcrypt
            password_bytes = password.encode('utf-8')
            stored_hash_bytes = stored_hash.encode('utf-8')
            
            if bcrypt.checkpw(password_bytes, stored_hash_bytes):
                # Login successful - update last login
                conn, cursor = get_db()
                cursor.execute("""
                    UPDATE users 
                    SET last_login = NOW() 
                    WHERE id = %s
                """, (user['id'],))
                conn.commit()
                cursor.close()
                conn.close()
                
                return {
                    "success": True,
                    "user": {
                        "username": user['username'],
                        "fullName": user['full_name'] or user['username'],
                        "isAdmin": bool(user['is_admin']),
                        "instanceId": user['instance_id']
                    }
                }
            else:
                print("Password mismatch")
                return {
                    "success": False,
                    "error": "Invalid username or password"
                }
        else:
            # Legacy password handling
            print("Warning: Plain text password in database")
            if password == stored_hash:
                # Upgrade to bcrypt
                new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                conn, cursor = get_db()
                cursor.execute("""
                    UPDATE users 
                    SET password_hash = %s 
                    WHERE id = %s
                """, (new_hash.decode('utf-8'), user['id']))
                conn.commit()
                cursor.close()
                conn.close()
                
                return {
                    "success": True,
                    "user": {
                        "username": user['username'],
                        "fullName": user['full_name'] or user['username'],
                        "isAdmin": bool(user['is_admin']),
                        "instanceId": user['instance_id']
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid username or password"
                }
            
    except Exception as e:
        print(f"Login error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "Server error during authentication"
        }

# ====== USER MANAGEMENT ======
@app.route('/api/users/create', methods=['POST', 'OPTIONS'])
@cors_headers
def create_user():
    """Create a new user with bcrypt hashed password"""
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    print(f"DEBUG create_user called with data: {request.json}")  # ADD THIS LINE
    
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        full_name = data.get('fullName', '').strip()
        is_admin = data.get('isAdmin', False)
        instance_id = data.get('instanceId', 1)
        
        if not username or not password:
            return {"success": False, "error": "Username and password required"}, 400
        
        if len(password) < 4:
            return {"success": False, "error": "Password must be at least 4 characters"}, 400
        
        # Hash password with bcrypt
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        conn, cursor = get_db()
        
        try:
            cursor.execute("""
                INSERT INTO users (instance_id, username, password_hash, full_name, is_admin)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (instance_id, username, password_hash.decode('utf-8'), full_name, is_admin))
            
            conn.commit()
            result = cursor.fetchone()
            user_id = result['id'] if result else None
            
            return {
                "success": True,
                "message": "User created successfully",
                "userId": user_id
            }
            
        except Exception as e:
            conn.rollback()
            error_msg = str(e)
            if "duplicate key" in error_msg.lower() or "unique constraint" in error_msg.lower():
                return {"success": False, "error": "Username already exists"}, 400
            else:
                return {"success": False, "error": error_msg}, 400
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Create user error: {e}")
        return {"success": False, "error": str(e)}, 500
    

@app.route('/api/users/list', methods=['GET', 'OPTIONS'])
@cors_headers
def list_users():
    """List all users for admin management"""
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    conn, cursor = None, None
    
    try:
        instance_id = request.args.get('instance_id', 1, type=int)
        
        conn, cursor = get_db()
        
        cursor.execute("""
            SELECT id, username, full_name, email, is_active, is_admin,
                   last_login,
                   created_at
            FROM users 
            WHERE instance_id = %s
            ORDER BY username
        """, (instance_id,))
        
        users = cursor.fetchall()
        
        # Format the results
        formatted_users = []
        for user in users:
            user_dict = dict(user)
            
            # Format dates safely
            if user_dict['last_login']:
                try:
                    if isinstance(user_dict['last_login'], datetime):
                        user_dict['last_login'] = user_dict['last_login'].strftime('%Y-%m-%d %H:%M')
                    else:
                        user_dict['last_login'] = str(user_dict['last_login'])
                except:
                    user_dict['last_login'] = str(user_dict['last_login'])
            else:
                user_dict['last_login'] = None
                
            if user_dict['created_at']:
                try:
                    if isinstance(user_dict['created_at'], datetime):
                        user_dict['created_date'] = user_dict['created_at'].strftime('%Y-%m-%d')
                    else:
                        user_dict['created_date'] = str(user_dict['created_at'])
                except:
                    user_dict['created_date'] = str(user_dict['created_at'])
            else:
                user_dict['created_date'] = None
            
            formatted_users.append(user_dict)
        
        return formatted_users
        
    except Exception as e:
        print(f"List users error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500
        
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass

@app.route('/api/clients/<client_name>', methods=['GET', 'OPTIONS'])
@cors_headers
def get_client_details(client_name):
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    conn, cursor = get_db()
    try:
        cursor.execute("""
            SELECT * FROM clients 
            WHERE instance_id = 1 
            AND name = %s 
            AND is_active = TRUE
        """, (client_name,))
        
        client = cursor.fetchone()
        
        if not client:
            return {"error": "Client not found"}, 404
        
        # Calculate amount due correctly
        prev_counter = client['prev_counter'] or 0
        current_counter = client['current_counter'] or 0
        kilowatt_price = float(client['kilowatt_price'] or 0)
        monthly_fee = float(client['monthly_fee'] or 0)
        amount_due = monthly_fee + (current_counter - prev_counter) * kilowatt_price
        
        return {
            "name": client['name'],
            "monthlyFee": monthly_fee,
            "prevCounter": prev_counter,
            "currentCounter": current_counter,
            "totalUsage": (current_counter - prev_counter),
            "kiloWattPrice": kilowatt_price,
            "amountUsage": amount_due,
            "prevBalance": float(client['prev_balance'] or 0),
            "currentBalance": float(client['current_balance'] or 0),
            "paymentAmt": float(client['payment_amt'] or 0),
            "newBalance": float(client['new_balance'] or 0),
            "lastPaidBy": client['last_paid_by'] or "",
            "payId": client['pay_id'] or "",
            "custID": client['cust_id'] or "",
            "isFirstPayment": float(client['payment_amt'] or 0) == 0
        }
        
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/clients', methods=['GET', 'OPTIONS'])
@cors_headers
def get_all_clients():
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    conn, cursor = get_db()
    try:
        cursor.execute("""
            SELECT * FROM clients 
            WHERE instance_id = 1 
            AND is_active = TRUE
            ORDER BY name
        """)
        
        clients = cursor.fetchall()
        
        result = []
        for client in clients:
            # Calculate amount due for each client
            amount_due = float(client['monthly_fee'] or 0) + \
                        (client['current_counter'] or 0 - client['prev_counter'] or 0) * \
                        float(client['kilowatt_price'] or 0)
            
            result.append({
                "name": client['name'],
                "monthlyFee": float(client['monthly_fee'] or 0),
                "prevCounter": client['prev_counter'] or 0,
                "currentCounter": client['current_counter'] or 0,
                "totalUsage": (client['current_counter'] or 0 - client['prev_counter'] or 0),
                "kiloWattPrice": float(client['kilowatt_price'] or 0),
                "amountUsage": amount_due,
                "prevBalance": float(client['prev_balance'] or 0),
                "currentBalance": float(client['current_balance'] or 0),
                "paymentAmt": float(client['payment_amt'] or 0),
                "newBalance": float(client['new_balance'] or 0),
                "lastPaidBy": client['last_paid_by'] or "",
                "payId": client['pay_id'] or "",
                "custID": client['cust_id'] or ""
            })
        
        return result
        
    except Exception as e:
        return {"error": str(e)}, 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/clients/search', methods=['GET', 'OPTIONS'])
@cors_headers
def search_clients():
    """Search clients by name"""
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    search_term = request.args.get('q', '').strip()
    
    if not search_term or len(search_term) < 2:
        return []
    
    conn, cursor = get_db()
    try:
        cursor.execute("""
            SELECT 
                id, name, 
                COALESCE(current_balance, 0) as current_balance,
                COALESCE(payment_amt, 0) as last_payment
            FROM clients 
            WHERE instance_id = 1 
            AND is_active = TRUE
            AND name ILIKE %s
            ORDER BY name
            LIMIT 10
        """, (f'%{search_term}%',))
        
        clients = cursor.fetchall()
        
        result = []
        for client in clients:
            result.append({
                "name": client['name'],
                "currentBalance": float(client['current_balance'] or 0),
                "lastPayment": float(client['last_payment'] or 0)
            })
        
        return result
        
    except Exception as e:
        print(f"Search clients error: {e}")
        return {"error": str(e)}, 500
    finally:
        cursor.close()
        conn.close()

# ====== PAYMENTS ======
@app.route('/api/payments/process', methods=['POST', 'OPTIONS'])
@cors_headers
def process_payment():
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    try:
        data = request.json
        client_name = data.get('clientName')
        amount = float(data.get('amount', 0))
        logged_in_user = data.get('loggedInUser', 'Guest')
        
        conn, cursor = get_db()
        
        # Get client
        cursor.execute("""
            SELECT * FROM clients 
            WHERE instance_id = 1 
            AND name = %s 
            AND is_active = TRUE
        """, (client_name,))
        
        client = cursor.fetchone()
        
        if not client:
            return {"error": "Client not found"}, 404
        
        # Check for recent duplicate (3 seconds)
        three_seconds_ago = datetime.now() - timedelta(seconds=3)
        cursor.execute("""
            SELECT payment_id FROM payments 
            WHERE instance_id = 1 
            AND client_id = %s 
            AND date_entered >= %s
            AND payment_amount = %s
            LIMIT 1
        """, (client['id'], three_seconds_ago, amount))
        
        duplicate = cursor.fetchone()
        
        if duplicate:
            return {
                "error": "Duplicate payment detected",
                "duplicatePaymentId": duplicate['payment_id']
            }, 409
        
        # Get next payment ID
        cursor.execute("SELECT MAX(payment_id) as max_id FROM payments WHERE instance_id = 1")
        last_payment = cursor.fetchone()
        next_payment_id = (last_payment['max_id'] or 1000) + 1
        
        # Get client data
        prev_counter = client['prev_counter'] or 0
        current_counter = client['current_counter'] or 0
        kilowatt_price = float(client['kilowatt_price'] or 0)
        monthly_fee = float(client['monthly_fee'] or 0)
        prev_balance = float(client['prev_balance'] or 0)
        payment_amt = float(client['payment_amt'] or 0)
        
        # Calculate correctly
        total_usage = current_counter - prev_counter
        usage_amount = total_usage * kilowatt_price
        amount_due = monthly_fee + usage_amount
        current_balance = prev_balance + amount_due
        
        is_first_payment = payment_amt == 0
        
        if is_first_payment:
            total_due_before = current_balance
        else:
            cursor.execute("""
                SELECT COALESCE(SUM(payment_amount), 0) as total 
                FROM payments 
                WHERE client_id = %s AND instance_id = 1
            """, (client['id'],))
            total_result = cursor.fetchone()
            total_previous_payments = float(total_result['total'] or 0)
            total_due_before = current_balance - total_previous_payments
        
        new_balance = total_due_before - amount
        new_payment_total = payment_amt + amount
        
        # Update client
        cursor.execute("""
            UPDATE clients 
            SET payment_amt = %s, 
                new_balance = %s, 
                last_paid_by = %s,
                amount_usage = %s,
                total_usage = %s,
                current_balance = %s,
                pay_id = CASE WHEN payment_amt = 0 THEN %s ELSE pay_id END,
                updated_at = NOW()
            WHERE id = %s
        """, (new_payment_total, new_balance, logged_in_user, 
              amount_due, total_usage, current_balance, str(next_payment_id), client['id']))
        
        # Insert payment
        cursor.execute("""
            INSERT INTO payments (
                instance_id, payment_id, client_id, date_entered, username,
                previous_balance_logged, total_due_before_payment, payment_amount,
                new_balance, customer_id, monthly_fee, previous_counter,
                current_counter, total_usage, kilowatt_price, amount_usage,
                previous_balance_data, current_balance_data, is_first_payment
            ) VALUES (1, %s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            next_payment_id, client['id'], logged_in_user,
            prev_balance, total_due_before, amount, new_balance,
            client['cust_id'], monthly_fee, prev_counter,
            current_counter, total_usage, kilowatt_price,
            amount_due, prev_balance, current_balance, is_first_payment
        ))
        
        conn.commit()
        
        return {
            "success": True,
            "clientName": client['name'],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "paymentId": str(next_payment_id),
            "monthlyFee": monthly_fee,
            "prevCounter": prev_counter,
            "currentCounter": current_counter,
            "totalUsage": total_usage,
            "kiloWattPrice": kilowatt_price,
            "amountUsage": amount_due,
            "prevBalanceLogged": prev_balance,
            "totalDueBeforePayment": total_due_before,
            "paymentAmount": amount,
            "newBalance": new_balance,
            "custID": client['cust_id'] or "",
            "isFirstPayment": is_first_payment
        }
        
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"Payment error: {e}")
        return {"error": str(e)}, 500
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()

@app.route('/api/payments', methods=['GET', 'OPTIONS'])
@cors_headers
def get_all_payments():
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    try:
        conn, cursor = get_db()
        
        query = """
            SELECT p.*, c.name as client_name 
            FROM payments p
            JOIN clients c ON p.client_id = c.id
            WHERE p.instance_id = 1
        """
        params = []
        
        client_filter = request.args.get('client', '')
        user_filter = request.args.get('user', '')
        from_date = request.args.get('from_date', '')
        to_date = request.args.get('to_date', '')
        
        if client_filter:
            query += " AND c.name LIKE %s"
            params.append(f'%{client_filter}%')
        
        if user_filter:
            query += " AND p.username LIKE %s"
            params.append(f'%{user_filter}%')
        
        if from_date:
            query += " AND DATE(p.date_entered) >= %s"
            params.append(from_date)
        
        if to_date:
            query += " AND DATE(p.date_entered) <= %s"
            params.append(to_date)
        
        query += " ORDER BY p.date_entered DESC"
        
        cursor.execute(query, params)
        payments = cursor.fetchall()
        
        result = []
        for payment in payments:
            payment_date = payment['date_entered']
            if isinstance(payment_date, datetime):
                date_str = payment_date.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = str(payment_date)
            
            result.append({
                "paymentId": payment['payment_id'],
                "clientName": payment['client_name'],
                "dateEntered": date_str,
                "user": payment['username'],
                "previousBalance": float(payment['previous_balance_logged'] or 0),
                "totalDueBeforePayment": float(payment['total_due_before_payment'] or 0),
                "paymentAmount": float(payment['payment_amount'] or 0),
                "newBalance": float(payment['new_balance'] or 0),
                "customerId": payment['customer_id'] or ""
            })
        
        cursor.close()
        conn.close()
        
        return result
        
    except Exception as e:
        print(f"Get payments error: {e}")
        return {"error": str(e)}, 500

@app.route('/api/payments/total-last', methods=['GET', 'OPTIONS'])
@cors_headers
def get_total_last_payment_amount():
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    try:
        conn, cursor = get_db()
        
        cursor.execute("""
            SELECT COALESCE(SUM(payment_amount), 0) as total 
            FROM payments 
            WHERE instance_id = 1
        """)
        
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {"total": float(result['total'] or 0)}
        
    except Exception as e:
        print(f"Total error: {e}")
        return {"error": str(e)}, 500

# ====== RECEIPT ======
@app.route('/api/receipt/by-id/<int:payment_id>', methods=['GET', 'OPTIONS'])
@cors_headers
def get_receipt_by_payment_id(payment_id):
    if request.method == 'OPTIONS':
        return {'status': 'preflight'}
    
    try:
        conn, cursor = get_db()
        
        cursor.execute("""
            SELECT p.*, c.name as client_name 
            FROM payments p
            JOIN clients c ON p.client_id = c.id
            WHERE p.instance_id = 1 
            AND p.payment_id = %s
        """, (payment_id,))
        
        payment = cursor.fetchone()
        
        if not payment:
            return {"error": "Payment not found"}, 404
        
        payment_date = payment['date_entered']
        if isinstance(payment_date, datetime):
            date_str = payment_date.strftime("%Y-%m-%d %H:%M")
        else:
            date_str = str(payment_date)
        
        receipt_data = {
            "clientName": payment['client_name'],
            "date": date_str,
            "monthlyFee": float(payment['monthly_fee'] or 0),
            "prevCounter": payment['previous_counter'] or 0,
            "currentCounter": payment['current_counter'] or 0,
            "totalUsage": payment['total_usage'] or 0,
            "kiloWattPrice": float(payment['kilowatt_price'] or 0),
            "amountUsage": float(payment['amount_usage'] or 0),
            "prevBalanceLogged": float(payment['previous_balance_logged'] or 0),
            "totalDueBeforePayment": float(payment['total_due_before_payment'] or 0),
            "paymentAmount": float(payment['payment_amount'] or 0),
            "newBalance": float(payment['new_balance'] or 0),
            "paymentId": str(payment['payment_id']),
            "custID": payment['customer_id'] or "",
            "isFirstPayment": bool(payment['is_first_payment'])
        }
        
        cursor.close()
        conn.close()
        
        return receipt_data
        
    except Exception as e:
        print(f"Receipt error: {e}")
        return {"error": str(e)}, 500

if __name__ == '__main__':
    print("=" * 80)
    print("🚀 Generator Payments System")
    print("=" * 80)
    print(f"💻 Local Access:  http://localhost:{PORT}/")
    print(f"🔧 Test API:      http://localhost:{PORT}/api/health")
    print("=" * 80)
    
    # Use PORT from environment variable (for Railway) or default to 8000
    app.run(host='0.0.0.0', port=PORT, debug=False, threaded=True)