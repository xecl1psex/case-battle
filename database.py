import sqlite3
import hashlib
import time

def init_db():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    
    # Добавляем новые колонки для статистики по режимам
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, 
        username TEXT UNIQUE, 
        password_hash TEXT,
        display_name TEXT,
        last_seen REAL DEFAULT 0,
        balance REAL DEFAULT 1000, 
        
        total_spent REAL DEFAULT 0, 
        total_won REAL DEFAULT 0, 
        
        spent_cases REAL DEFAULT 0,
        won_cases REAL DEFAULT 0,
        cases_opened INTEGER DEFAULT 0,
        
        spent_upgrades REAL DEFAULT 0,
        won_upgrades REAL DEFAULT 0,
        total_upgrades INTEGER DEFAULT 0,
        
        spent_contracts REAL DEFAULT 0,
        won_contracts REAL DEFAULT 0,
        total_contracts INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY, 
        user_id INTEGER,
        name TEXT, 
        price REAL, 
        rarity TEXT, 
        image TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS drop_feed (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        user_name TEXT,
        item_name TEXT,
        item_price REAL,
        item_image TEXT,
        case_name TEXT,
        timestamp REAL
    )''')

    # ★ НОВАЯ ТАБЛИЦА: ИСТОРИЯ ТРАНЗАКЦИЙ ★
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        type TEXT,
        amount REAL,
        balance_after REAL,
        description TEXT,
        timestamp REAL
    )''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, display_name):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash, display_name, balance) VALUES (?, ?, ?, ?)", 
                  (username, hash_password(password), display_name, 1000))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return {"success": True, "user_id": user_id, "balance": 1000}
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "message": "Этот логин уже занят!"}

def login_user(username, password):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("SELECT id, password_hash, balance, display_name FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and user[1] == hash_password(password):
        return {"success": True, "user_id": user[0], "balance": user[2], "display_name": user[3]}
    return {"success": False, "message": "Неверный логин или пароль!"}

def get_user_data(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''SELECT balance, total_spent, total_won, cases_opened, display_name, last_seen, 
                 total_upgrades, total_contracts,
                 spent_cases, won_cases, spent_upgrades, won_upgrades, spent_contracts, won_contracts 
                 FROM users WHERE id = ?''', (user_id,))
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
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def update_stats(user_id, spent=0, won=0, cases=0, upgrades=0, contracts=0, 
                  spent_cases=0, won_cases=0, spent_upgrades=0, won_upgrades=0, spent_contracts=0, won_contracts=0):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('''UPDATE users SET 
        total_spent = total_spent + ?, 
        total_won = total_won + ?, 
        cases_opened = cases_opened + ?, 
        total_upgrades = total_upgrades + ?, 
        total_contracts = total_contracts + ?,
        spent_cases = spent_cases + ?, 
        won_cases = won_cases + ?,
        spent_upgrades = spent_upgrades + ?, 
        won_upgrades = won_upgrades + ?,
        spent_contracts = spent_contracts + ?, 
        won_contracts = won_contracts + ?
        WHERE id = ?''', 
        (spent, won, cases, upgrades, contracts, 
         spent_cases, won_cases, spent_upgrades, won_upgrades, spent_contracts, won_contracts, user_id))
    conn.commit()
    conn.close()

def update_last_seen(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("UPDATE users SET last_seen = ? WHERE id = ?", (time.time(), user_id))
    conn.commit()
    conn.close()

def add_item(user_id, name, price, rarity, image=""):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("INSERT INTO inventory (user_id, name, price, rarity, image) VALUES (?, ?, ?, ?, ?)", 
              (user_id, name, price, rarity, image))
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return item_id

def get_inventory(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("SELECT id, name, price, rarity, image FROM inventory WHERE user_id = ?", (user_id,))
    items = [{"id": row[0], "name": row[1], "price": row[2], "rarity": row[3], "image": row[4]} for row in c.fetchall()]
    conn.close()
    return items

def remove_item(user_id, item_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("DELETE FROM inventory WHERE id = ? AND user_id = ?", (item_id, user_id))
    conn.commit()
    conn.close()

def sell_item(user_id, item_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("SELECT price FROM inventory WHERE id = ? AND user_id = ?", (item_id, user_id))
    res = c.fetchone()
    if not res:
        conn.close()
        return 0
    price = res[0]
    c.execute("DELETE FROM inventory WHERE id = ? AND user_id = ?", (item_id, user_id))
    c.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (price, user_id))
    conn.commit()
    conn.close()
    return price

def add_drop_feed(user_id, user_name, item_name, item_price, item_image, case_name):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("INSERT INTO drop_feed (user_id, user_name, item_name, item_price, item_image, case_name, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)", 
              (user_id, user_name, item_name, item_price, item_image, case_name, time.time()))
    conn.commit()
    c.execute("DELETE FROM drop_feed WHERE id NOT IN (SELECT id FROM drop_feed ORDER BY timestamp DESC LIMIT 50)")
    conn.commit()
    conn.close()

def get_drop_feed(limit=20):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("SELECT user_name, item_name, item_price, item_image, case_name, timestamp FROM drop_feed ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [{"user": row[0], "item": row[1], "price": row[2], "image": row[3], "case": row[4], "time": row[5]} for row in rows]

def get_online_users():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    current_time = time.time()
    c.execute("SELECT display_name FROM users WHERE (last_seen > ?)", (current_time - 300,))
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

# ★ НОВАЯ ФУНКЦИЯ: ДОБАВЛЕНИЕ ЗАПИСИ В ИСТОРИЮ ★
def add_transaction(user_id, type, amount, balance_after, description=""):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("INSERT INTO transactions (user_id, type, amount, balance_after, description, timestamp) VALUES (?, ?, ?, ?, ?, ?)", 
              (user_id, type, amount, balance_after, description, time.time()))
    conn.commit()
    conn.close()

# ★ НОВАЯ ФУНКЦИЯ: ПОЛУЧЕНИЕ ИСТОРИИ ★
def get_transactions(user_id, limit=20):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("SELECT type, amount, balance_after, description, timestamp FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return [{"type": row[0], "amount": row[1], "balance_after": row[2], "description": row[3], "time": row[4]} for row in rows]
