import psycopg2
import hashlib
import time
import os

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    if not DATABASE_URL:
        raise ValueError("Переменная окружения DATABASE_URL не задана!")
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY, 
        username TEXT UNIQUE, 
        password_hash TEXT,
        display_name TEXT,
        last_seen DOUBLE PRECISION DEFAULT 0,
        balance DOUBLE PRECISION DEFAULT 1000, 
        
        total_spent DOUBLE PRECISION DEFAULT 0, 
        total_won DOUBLE PRECISION DEFAULT 0, 
        
        spent_cases DOUBLE PRECISION DEFAULT 0,
        won_cases DOUBLE PRECISION DEFAULT 0,
        cases_opened INTEGER DEFAULT 0,
        
        spent_upgrades DOUBLE PRECISION DEFAULT 0,
        won_upgrades DOUBLE PRECISION DEFAULT 0,
        total_upgrades INTEGER DEFAULT 0,
        
        spent_contracts DOUBLE PRECISION DEFAULT 0,
        won_contracts DOUBLE PRECISION DEFAULT 0,
        total_contracts INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id SERIAL PRIMARY KEY, 
        user_id INTEGER,
        name TEXT, 
        price DOUBLE PRECISION, 
        rarity TEXT, 
        image TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS drop_feed (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        user_name TEXT,
        item_name TEXT,
        item_price DOUBLE PRECISION,
        item_image TEXT,
        case_name TEXT,
        timestamp DOUBLE PRECISION
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        type TEXT,
        amount DOUBLE PRECISION,
        balance_after DOUBLE PRECISION,
        description TEXT,
        timestamp DOUBLE PRECISION
    )''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, display_name):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, display_name, balance) VALUES (%s, %s, %s, %s) RETURNING id", 
                  (username, hash_password(password), display_name, 1000))
        user_id = c.fetchone()[0]
        conn.commit()
        return {"success": True, "user_id": user_id, "balance": 1000}
    except psycopg2.IntegrityError:
        conn.rollback()
        return {"success": False, "message": "Этот логин уже занят!"}
    finally:
        conn.close()

def login_user(username, password):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, password_hash, balance, display_name FROM users WHERE username = %s", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and user[1] == hash_password(password):
        return {"success": True, "user_id": user[0], "balance": user[2], "display_name": user[3]}
    return {"success": False, "message": "Неверный логин или пароль!"}

def get_user_data(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''SELECT balance, total_spent, total_won, cases_opened, display_name, last_seen, 
                 total_upgrades, total_contracts,
                 spent_cases, won_cases, spent_upgrades, won_upgrades, spent_contracts, won_contracts 
                 FROM users WHERE id = %s''', (user_id,))
    data = c.fetchone()
    conn.close()
    if data:
        return {
            "balance": data[0], "spent": data[1], "won": data[2], "opened": data[3], 
            "display_name": data[4], "last_seen": data[5], "upgrades": data[6], "contracts": data[7],
            "spent_cases": data[8], "won_cases": data[9], 
            "spent_upgrades": data[10], "won_upgrades": data[11],
            "spent_contracts": data[12], "won_contracts": data[13]
        }
    return None

def update_balance(user_id, amount):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, user_id))
    conn.commit()
    conn.close()

def update_stats(user_id, spent=0, won=0, cases=0, upgrades=0, contracts=0, 
                  spent_cases=0, won_cases=0, spent_upgrades=0, won_upgrades=0, spent_contracts=0, won_contracts=0):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''UPDATE users SET 
        total_spent = total_spent + %s, 
        total_won = total_won + %s, 
        cases_opened = cases_opened + %s, 
        total_upgrades = total_upgrades + %s, 
        total_contracts = total_contracts + %s,
        spent_cases = spent_cases + %s, 
        won_cases = won_cases + %s,
        spent_upgrades = spent_upgrades + %s, 
        won_upgrades = won_upgrades + %s,
        spent_contracts = spent_contracts + %s, 
        won_contracts = won_contracts + %s
        WHERE id = %s''', 
        (spent, won, cases, upgrades, contracts, 
         spent_cases, won_cases, spent_upgrades, won_upgrades, spent_contracts, won_contracts, user_id))
    conn.commit()
    conn.close()

def update_last_seen(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET last_seen = %s WHERE id = %s", (time.time(), user_id))
    conn.commit()
    conn.close()

def add_item(user_id, name, price, rarity, image=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO inventory (user_id, name, price, rarity, image) VALUES (%s, %s, %s, %s, %s) RETURNING id", 
              (user_id, name, price, rarity, image))
    item_id = c.fetchone()[0]
    conn.commit()
    conn.close()
    return item_id

def get_inventory(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name, price, rarity, image FROM inventory WHERE user_id = %s", (user_id,))
    items = [{"id": row[0], "name": row[1], "price": row[2], "rarity": row[3], "image": row[4]} for row in c.fetchall()]
    conn.close()
    return items

def remove_item(user_id, item_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM inventory WHERE id = %s AND user_id = %s", (item_id, user_id))
    conn.commit()
    conn.close()

def sell_item(user_id, item_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT price FROM inventory WHERE id = %s AND user_id = %s", (item_id, user_id))
    res = c.fetchone()
    if not res:
        conn.close()
        return 0
    price = res[0]
    c.execute("DELETE FROM inventory WHERE id = %s AND user_id = %s", (item_id, user_id))
    c.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (price, user_id))
    conn.commit()
    conn.close()
    return price

def add_drop_feed(user_id, user_name, item_name, item_price, item_image, case_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO drop_feed (user_id, user_name, item_name, item_price, item_image, case_name, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
              (user_id, user_name, item_name, item_price, item_image, case_name, time.time()))
    conn.commit()
    c.execute("DELETE FROM drop_feed WHERE id NOT IN (SELECT id FROM drop_feed ORDER BY timestamp DESC LIMIT 50)")
    conn.commit()
    conn.close()

def get_drop_feed(limit=20):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_name, item_name, item_price, item_image, case_name, timestamp FROM drop_feed ORDER BY timestamp DESC LIMIT %s", (limit,))
    rows = c.fetchall()
    conn.close()
    return [{"user": row[0], "item": row[1], "price": row[2], "image": row[3], "case": row[4], "time": row[5]} for row in rows]

def get_online_users():
    conn = get_connection()
    c = conn.cursor()
    current_time = time.time()
    c.execute("SELECT display_name FROM users WHERE (last_seen > %s)", (current_time - 300,))
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def add_transaction(user_id, type, amount, balance_after, description=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO transactions (user_id, type, amount, balance_after, description, timestamp) VALUES (%s, %s, %s, %s, %s, %s)", 
              (user_id, type, amount, balance_after, description, time.time()))
    conn.commit()
    conn.close()

def get_transactions(user_id, limit=20):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT type, amount, balance_after, description, timestamp FROM transactions WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return [{"type": row[0], "amount": row[1], "balance_after": row[2], "description": row[3], "time": row[4]} for row in rows]

def reset_user_stats(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''UPDATE users SET 
        total_spent = 0, total_won = 0, cases_opened = 0, total_upgrades = 0, total_contracts = 0,
        spent_cases = 0, won_cases = 0, spent_upgrades = 0, won_upgrades = 0, spent_contracts = 0, won_contracts = 0
        WHERE id = %s''', (user_id,))
    conn.commit()
    conn.close()
