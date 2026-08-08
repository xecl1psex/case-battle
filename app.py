import sys
import subprocess
import importlib
import urllib.parse
import math
import random
import os
import threading
import time
import sqlite3

def install_and_import(package):
    try:
        importlib.import_module(package)
    except ImportError:
        print(f"⚠️ Библиотека {package} не найдена. Скачиваю...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

required = ["flask"]
for lib in required:
    install_and_import(lib)

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import database
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_fallback_key_for_local_dev')
db_lock = threading.Lock()

# ★ ФИЛЬТР ФОРМАТИРОВАНИЯ ЧИСЕЛ (с пробелами между тысяч) ★
def format_thousands(value):
    try:
        return f"{int(value):,}".replace(',', ' ')
    except (ValueError, TypeError):
        return str(value)

# Регистрируем фильтр в Jinja2
app.jinja_env.filters['thousands'] = format_thousands

# ★ ЗАПРЕТ КЕШИРОВАНИЯ ДЛЯ БРАУЗЕРА ★
@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

database.init_db()

@app.before_request
def update_online_status():
    if 'user_id' in session:
        database.update_last_seen(session['user_id'])

# ===== ИКОНКИ =====
def get_icon(weapon_type, color_hex):
    bg_color = "#1e1e2e"
    outline_color = "#222" if color_hex == "#000000" else color_hex

    if weapon_type in ["Пистолет", "Пистолет-пулемёт"]:
        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 80" width="100%" height="100%">
            <rect width="100%" height="100%" fill="{bg_color}" rx="10"/>
            <g stroke="{outline_color}" stroke-width="4.5" fill="none" stroke-linejoin="round" stroke-linecap="round">
                <rect x="25" y="40" width="45" height="12" rx="2"/>
                <rect x="70" y="44" width="4" height="4" rx="1"/>
                <rect x="35" y="36" width="10" height="20" rx="2"/>
                <path d="M 30 52 L 25 68 L 45 68 L 50 52 Z"/>
            </g>
        </svg>
        '''
    elif weapon_type == "Дробовик":
        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 130 80" width="100%" height="100%">
            <rect width="100%" height="100%" fill="{bg_color}" rx="10"/>
            <g stroke="{outline_color}" stroke-width="4.5" fill="none" stroke-linejoin="round">
                <rect x="20" y="40" width="80" height="12" rx="2"/>
                <rect x="25" y="40" width="15" height="12" rx="2"/>
                <rect x="75" y="52" width="12" height="16" rx="2"/>
                <path d="M 90 40 L 110 40 L 110 52 L 90 52 Z"/>
            </g>
        </svg>
        '''
    elif weapon_type in ["Винтовка", "Штурмовая винтовка"]:
        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 80" width="100%" height="100%">
            <rect width="100%" height="100%" fill="{bg_color}" rx="10"/>
            <g stroke="{outline_color}" stroke-width="4.5" fill="none" stroke-linejoin="round">
                <rect x="20" y="40" width="85" height="12" rx="2"/>
                <rect x="45" y="52" width="12" height="16" rx="2"/>
                <rect x="80" y="52" width="12" height="16" rx="2"/>
                <rect x="65" y="35" width="8" height="8" rx="2"/>
                <path d="M 95 40 L 115 40 L 115 52 L 95 52 Z"/>
            </g>
        </svg>
        '''
    elif weapon_type == "Снайперская":
        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 80" width="100%" height="100%">
            <rect width="100%" height="100%" fill="{bg_color}" rx="10"/>
            <g stroke="{outline_color}" stroke-width="4.5" fill="none" stroke-linejoin="round">
                <rect x="20" y="40" width="125" height="12" rx="2"/>
                <rect x="50" y="52" width="12" height="16" rx="2"/>
                <rect x="105" y="52" width="12" height="16" rx="2"/>
                <rect x="115" y="28" width="25" height="14" rx="2"/>
                <path d="M 135 40 L 155 40 L 155 52 L 135 52 Z"/>
            </g>
        </svg>
        '''
    elif weapon_type == "Нож":
        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="100%" height="100%">
            <rect width="100%" height="100%" fill="{bg_color}" rx="10"/>
            <g stroke="{outline_color}" stroke-width="4.5" fill="none" stroke-linejoin="round" stroke-linecap="round">
                <polygon points="40,5 52,45 28,45"/>
                <line x1="40" y1="5" x2="42" y2="5" stroke-width="3"/>
                <rect x="30" y="43" width="20" height="4" rx="1"/>
                <rect x="35" y="45" width="10" height="25" rx="2"/>
                <circle cx="40" cy="52" r="2.5" fill="{outline_color}"/>
                <circle cx="40" cy="62" r="2.5" fill="{outline_color}"/>
            </g>
        </svg>
        '''
    elif weapon_type == "Перчатки":
        svg = f'''
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="100%" height="100%">
            <rect width="100%" height="100%" fill="{bg_color}" rx="10"/>
            <g stroke="{outline_color}" stroke-width="4.5" fill="none" stroke-linejoin="round" stroke-linecap="round">
                <path d="M 20 35 L 60 35 L 65 35 Q 70 35 70 45 Q 70 65 65 65 L 20 65 Q 15 65 15 45 Q 15 35 20 35 Z"/>
                <path d="M 20 35 Q 10 35 10 45 Q 10 55 20 55"/>
                <rect x="20" y="65" width="40" height="8" rx="2"/>
                <path d="M 35 45 L 55 45" stroke-width="3"/>
                <path d="M 35 55 L 55 55" stroke-width="3"/>
            </g>
        </svg>
        '''
    else:
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80"><rect width="100%" height="100%" fill="{bg_color}" rx="10"/><circle cx="40" cy="40" r="20" stroke="{outline_color}" stroke-width="4" fill="none"/></svg>'

    encoded_svg = urllib.parse.quote(svg)
    return f"data:image/svg+xml;charset=utf-8,{encoded_svg}"

# ===== ЦВЕТА И НАЗВАНИЯ =====
RARITY_NAMES = {
    "common": "Обычный", "uncommon": "Необычный", "rare": "Редкий",
    "epic": "Эпический", "legendary": "Легендарный", "mythic": "Мифический"
}
RARITY_COLORS = {
    "common": "#8a8a8a", "uncommon": "#1a8a1a", "rare": "#3a7aff",
    "epic": "#b03aff", "legendary": "#ff8c00", "mythic": "#ff0000"
}

# ===== РАСШИРЕННЫЙ ПУЛ ЦЕН (ДО 10 МИЛЛИОНОВ) =====
ALL_ITEMS = []
WEAPON_TYPES = ["Пистолет", "Пистолет-пулемёт", "Дробовик", "Винтовка", "Штурмовая винтовка", "Снайперская", "Нож", "Перчатки"]

prices = []
for p in range(1, 10, 1): prices.append(p)
for p in range(10, 100, 5): prices.append(p)
for p in range(100, 1000, 10): prices.append(p)
for p in range(1000, 10000, 50): prices.append(p)
for p in range(10000, 50000, 100): prices.append(p)
for p in range(50000, 200000, 250): prices.append(p)
for p in range(200000, 500000, 500): prices.append(p)
for p in range(500000, 1000000, 1000): prices.append(p)
for p in range(1000000, 10000001, 5000): prices.append(p)

rarity_price_ranges = {
    "common": [p for p in prices if p <= 80],
    "uncommon": [p for p in prices if 90 <= p <= 300],
    "rare": [p for p in prices if 310 <= p <= 800],
    "epic": [p for p in prices if 900 <= p <= 4000],
    "legendary": [p for p in prices if 5000 <= p <= 20000],
    "mythic": [p for p in prices if p >= 25000]
}

ADJECTIVES = [
    "Багровый", "Лазурный", "Изумрудный", "Золотой", "Серебряный", "Алмазный", "Рубиновый", "Сапфировый",
    "Янтарный", "Топазовый", "Аметистовый", "Жемчужный", "Бронзовый", "Платиновый", "Титановый", "Стальной",
    "Гранитный", "Обсидиановый", "Неоновый", "Плазменный", "Космический", "Лунный", "Солнечный", "Звёздный",
    "Теневой", "Молниевой", "Огненный", "Ледяной", "Ветреный", "Земляной", "Водяной", "Древний", "Могучий",
    "Священный", "Проклятый", "Дикий", "Безжалостный", "Смертельный", "Бесконечный", "Вечный", "Глубинный",
    "Раскалённый", "Леденящий", "Бушующий", "Неукротимый", "Призрачный", "Скрытый", "Благородный", "Королевский"
]
NOUNS = [
    "Пламя", "Лёд", "Гром", "Молния", "Шторм", "Вихрь", "Предел", "Бездна", "Хаос", "Порядок",
    "Свет", "Тьма", "Каратель", "Демон", "Ангел", "Торнадо", "Ураган", "Скала", "Гранит", "Смерч",
    "Клык", "Коготь", "Зверь", "Призрак", "Фантом", "Космос", "Искра", "Огонь", "Вода", "Земля",
    "Воздух", "Ночь", "День", "Вихрь", "Скала", "Ярость", "Гнев", "Бездна", "Сокол", "Орёл",
    "Дракон", "Волк", "Тигр", "Лев", "Феникс", "Гидра", "Цербер", "Титан", "Колосс", "Легенда"
]

for t in WEAPON_TYPES:
    for r in RARITY_NAMES.keys():
        if t in ["Нож", "Перчатки"] and r in ["common", "uncommon", "rare"]:
            continue
        
        min_price_override = 200 if t in ["Нож", "Перчатки"] else 0
        available = [p for p in rarity_price_ranges[r] if p >= min_price_override]
        if not available:
            available = [p for p in prices if p >= min_price_override]
        
        count = 12 if r in ["common", "uncommon"] else 15
        for _ in range(count):
            price = random.choice(available)
            adj = random.choice(ADJECTIVES)
            noun = random.choice(NOUNS)
            name = f"{t} «{adj} {noun}»"
            color = RARITY_COLORS[r]
            image = get_icon(t, color)
            ALL_ITEMS.append({
                "name": name,
                "type": t,
                "price": price,
                "rarity": r,
                "image": image
            })

ALL_ITEMS.sort(key=lambda x: x['price'])

# ===== КЕЙСЫ =====
def generate_case_drop(case_price, items_count=50):
    if case_price <= 20:
        min_multiplier = 0.05
        abs_min_price = 0.0
        max_multiplier = 5
        cheap_threshold = 0.8
        trash_ratio = 0.70
    elif case_price <= 50:
        min_multiplier = 0.05
        abs_min_price = 2.5
        max_multiplier = 6
        cheap_threshold = 0.7
        trash_ratio = 0.60
    elif case_price <= 100:
        min_multiplier = 0.10
        abs_min_price = 10.0
        max_multiplier = 8
        cheap_threshold = 0.6
        trash_ratio = 0.45
    elif case_price <= 500:
        min_multiplier = 0.15
        abs_min_price = 0.0
        max_multiplier = 12
        cheap_threshold = 0.6
        trash_ratio = 0.30
    elif case_price <= 2000:
        min_multiplier = 0.30
        abs_min_price = 0.0
        max_multiplier = 16
        cheap_threshold = 0.5
        trash_ratio = 0.15
    elif case_price <= 10000:
        min_multiplier = 0.30
        abs_min_price = 0.0
        max_multiplier = 20
        cheap_threshold = 0.4
        trash_ratio = 0.10
    else:
        min_multiplier = 0.25
        abs_min_price = 0.0
        max_multiplier = 30
        cheap_threshold = 0.3
        trash_ratio = 0.08
    
    min_price = max(case_price * min_multiplier, abs_min_price)
    max_price = case_price * max_multiplier
    
    if case_price <= 20:
        jackpot_range = (100, 1500)
    elif case_price <= 50:
        jackpot_range = (500, 3000)
    elif case_price <= 100:
        jackpot_range = (2000, 10000)
    elif case_price <= 500:
        jackpot_range = (5000, 50000)
    elif case_price <= 2000:
        jackpot_range = (50000, 200000)
    elif case_price <= 10000:
        jackpot_range = (100000, 1000000)
    else:
        jackpot_range = (500000, 10000000)
    
    jackpot_candidates = [item for item in ALL_ITEMS if jackpot_range[0] <= item['price'] <= jackpot_range[1]]
    random.shuffle(jackpot_candidates)
    jackpots = jackpot_candidates[:3]
    
    normal_count = items_count - len(jackpots)
    
    valid_items = [item for item in ALL_ITEMS if min_price <= item['price'] <= max_price and item not in jackpots]
    if len(valid_items) < normal_count:
        valid_items = [item for item in ALL_ITEMS if min_price <= item['price'] <= case_price * (max_multiplier + 5) and item not in jackpots]
    if len(valid_items) < normal_count:
        valid_items = [item for item in ALL_ITEMS if item not in jackpots]
    
    cheap_items = [item for item in valid_items if item['price'] <= case_price * cheap_threshold]
    random.shuffle(cheap_items)
    
    normal_pool = []
    cheap_count = int(normal_count * trash_ratio)
    for i in range(min(cheap_count, len(cheap_items))):
        normal_pool.append(cheap_items[i])
    
    remaining = normal_count - len(normal_pool)
    if remaining > 0:
        other_items = [item for item in valid_items if item not in normal_pool]
        random.shuffle(other_items)
        normal_pool.extend(other_items[:remaining])
    
    while len(normal_pool) < normal_count:
        normal_pool.append(random.choice(ALL_ITEMS))
    
    selected = jackpots + normal_pool
    random.shuffle(selected)
    
    weights = []
    for item in selected:
        weight = 1000 / ((item['price'] + 1) ** 0.45)
        weight = weight * random.uniform(0.9, 1.1)
        weights.append(weight)
    
    total_weight = sum(weights)
    raw_chances = [(w / total_weight) * 100 for w in weights]
    chances = [round(c, 2) for c in raw_chances]
    
    diff = 100.0 - sum(chances)
    if diff != 0:
        chances[-1] = round(chances[-1] + diff, 2)
    chances = [float(f"{c:.2f}") for c in chances]
    
    drop_list = []
    for i, item in enumerate(selected):
        drop_list.append({
            "name": item["name"],
            "type": item["type"],
            "price": item["price"],
            "chance": chances[i],
            "rarity": item["rarity"],
            "image": item["image"]
        })
    drop_list.sort(key=lambda x: x["chance"], reverse=True)
    return drop_list

CASES = {
    "entry": {"name": "Входной билет", "price": 10, "image": get_icon("Пистолет", "#8a8a8a"), "drop_list": generate_case_drop(10, 50)},
    "starter": {"name": "Новичок", "price": 15, "image": get_icon("Пистолет", "#8a8a8a"), "drop_list": generate_case_drop(15, 50)},
    "common": {"name": "Базовый кейс", "price": 25, "image": get_icon("Пистолет", "#8a8a8a"), "drop_list": generate_case_drop(25, 50)},
    "classic": {"name": "Классический кейс", "price": 50, "image": get_icon("Пистолет", "#8a8a8a"), "drop_list": generate_case_drop(50, 50)},
    "cyberpunk": {"name": "Киберпанк 2077", "price": 100, "image": get_icon("Пистолет-пулемёт", "#3a7aff"), "drop_list": generate_case_drop(100, 50)},
    "space": {"name": "Космическая бездна", "price": 250, "image": get_icon("Винтовка", "#b03aff"), "drop_list": generate_case_drop(250, 50)},
    "firestorm": {"name": "Огненный шторм", "price": 500, "image": get_icon("Дробовик", "#ff8c00"), "drop_list": generate_case_drop(500, 50)},
    "frostbite": {"name": "Ледяная стужа", "price": 800, "image": get_icon("Снайперская", "#3a7aff"), "drop_list": generate_case_drop(800, 50)},
    "melee": {"name": "Клинки и перчатки", "price": 1200, "image": get_icon("Нож", "#b03aff"), "drop_list": generate_case_drop(1200, 50)},
    "lightning": {"name": "Гром и молния", "price": 1000, "image": get_icon("Перчатки", "#b03aff"), "drop_list": generate_case_drop(1000, 50)},
    "pyro": {"name": "Пиромант", "price": 1800, "image": get_icon("Дробовик", "#ff8c00"), "drop_list": generate_case_drop(1800, 50)},
    "cryo": {"name": "Криомант", "price": 3200, "image": get_icon("Винтовка", "#3a7aff"), "drop_list": generate_case_drop(3200, 50)},
    "ash": {"name": "Пепел", "price": 2500, "image": get_icon("Снайперская", "#3a7aff"), "drop_list": generate_case_drop(2500, 50)},
    "void": {"name": "Пустота", "price": 4500, "image": get_icon("Нож", "#ff0000"), "drop_list": generate_case_drop(4500, 50)},
    "legend": {"name": "Легендарный арсенал", "price": 2000, "image": get_icon("Штурмовая винтовка", "#ff8c00"), "drop_list": generate_case_drop(2000, 50)},
    "mythic": {"name": "Мифический предел", "price": 3500, "image": get_icon("Нож", "#ff0000"), "drop_list": generate_case_drop(3500, 50)},
    "golden": {"name": "Золотая лихорадка", "price": 5000, "image": get_icon("Пистолет", "#ff8c00"), "drop_list": generate_case_drop(5000, 50)},
    "titan": {"name": "Титан", "price": 7500, "image": get_icon("Перчатки", "#ff0000"), "drop_list": generate_case_drop(7500, 50)},
    "shadow": {"name": "Теневой охотник", "price": 10000, "image": get_icon("Снайперская", "#b03aff"), "drop_list": generate_case_drop(10000, 50)},
    "eternal": {"name": "Вечность", "price": 15000, "image": get_icon("Штурмовая винтовка", "#ff8c00"), "drop_list": generate_case_drop(15000, 50)},
    "abyss": {"name": "Бездна", "price": 25000, "image": get_icon("Нож", "#ff0000"), "drop_list": generate_case_drop(25000, 50)},
    "dragon": {"name": "Драконья сокровищница", "price": 50000, "image": get_icon("Дробовик", "#ff8c00"), "drop_list": generate_case_drop(50000, 50)},
    "immortal": {"name": "Бессмертный арсенал", "price": 100000, "image": get_icon("Винтовка", "#b03aff"), "drop_list": generate_case_drop(100000, 50)},
    "godlike": {"name": "Божественный предел", "price": 500000, "image": get_icon("Нож", "#ff0000"), "drop_list": generate_case_drop(500000, 50)},
    "omega": {"name": "Омега-кейс", "price": 1000000, "image": get_icon("Штурмовая винтовка", "#ff0000"), "drop_list": generate_case_drop(1000000, 50)}
}

# ---- СТРАНИЦЫ ----
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user_data = database.get_user_data(session['user_id'])
    if not user_data:
        return redirect(url_for('login_page'))
    feed = database.get_drop_feed(15)
    online_users = database.get_online_users()
    return render_template('index.html', balance=user_data['balance'], feed=feed, now=time.time(), online_users=online_users, page='home')

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        result = database.login_user(username, password)
        if result['success']:
            session['user_id'] = result['user_id']
            return redirect(url_for('index'))
        return render_template('login.html', error=result['message'])
    return render_template('login.html', error=None, page='login')

@app.route('/register', methods=['POST'])
def register_page():
    username = request.form.get('username')
    password = request.form.get('password')
    display_name = request.form.get('display_name')
    
    if not display_name:
        return render_template('login.html', error="Введите отображаемый ник!")
    
    result = database.register_user(username, password, display_name)
    if result['success']:
        session['user_id'] = result['user_id']
        return redirect(url_for('index'))
    return render_template('login.html', error=result['message'], page='login')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/cases')
def cases():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user_data = database.get_user_data(session['user_id'])
    if not user_data:
        return redirect(url_for('login_page'))
    feed = database.get_drop_feed(15)
    online_users = database.get_online_users()
    return render_template('cases.html', cases=CASES, balance=user_data['balance'], feed=feed, now=time.time(), online_users=online_users, page='cases')

@app.route('/case/<case_type>')
def case_page(case_type):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    case = CASES.get(case_type)
    if not case:
        return "Кейс не найден", 404
    user_data = database.get_user_data(session['user_id'])
    if not user_data:
        return redirect(url_for('login_page'))
    feed = database.get_drop_feed(15)
    online_users = database.get_online_users()
    return render_template('case_page.html', case=case, case_type=case_type, balance=user_data['balance'], 
                          RARITY_COLORS=RARITY_COLORS, RARITY_NAMES=RARITY_NAMES, feed=feed, now=time.time(), online_users=online_users, page='cases')

@app.route('/upgrade')
def upgrade():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user_data = database.get_user_data(session['user_id'])
    if not user_data:
        return redirect(url_for('login_page'))
    feed = database.get_drop_feed(15)
    online_users = database.get_online_users()
    return render_template('upgrade.html', inventory=database.get_inventory(session['user_id']), all_skins=ALL_ITEMS, balance=user_data['balance'],
                          RARITY_COLORS=RARITY_COLORS, RARITY_NAMES=RARITY_NAMES, feed=feed, now=time.time(), online_users=online_users, page='upgrade')

@app.route('/contracts')
def contracts():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user_data = database.get_user_data(session['user_id'])
    if not user_data:
        return redirect(url_for('login_page'))
    feed = database.get_drop_feed(15)
    online_users = database.get_online_users()
    return render_template('contracts.html', inventory=database.get_inventory(session['user_id']), all_skins=ALL_ITEMS, balance=user_data['balance'],
                          RARITY_COLORS=RARITY_COLORS, RARITY_NAMES=RARITY_NAMES, feed=feed, now=time.time(), online_users=online_users, page='contracts')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    user_data = database.get_user_data(session['user_id'])
    if not user_data:
        return redirect(url_for('login_page'))
    inventory = database.get_inventory(session['user_id'])
    feed = database.get_drop_feed(20)
    online_users = database.get_online_users()
    return render_template('profile.html', stats=user_data, inventory=inventory, balance=user_data['balance'], feed=feed,
                          RARITY_COLORS=RARITY_COLORS, RARITY_NAMES=RARITY_NAMES, now=time.time(), online_users=online_users, page='profile')

# ---- API (КЕЙСЫ) ----
@app.route('/api/open_case', methods=['POST'])
def open_case():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Не авторизован"})
    
    user_id = session['user_id']
    case_type = request.json.get('case_type')
    case = CASES[case_type]
    
    with db_lock:
        user_data = database.get_user_data(user_id)
        if not user_data:
            return jsonify({"success": False, "message": "Пользователь не найден"})
        
        if user_data['balance'] < case['price']:
            return jsonify({"success": False, "message": "Недостаточно средств"})
        
        new_balance = user_data['balance'] - case['price']
        database.update_balance(user_id, -case['price'])
        database.add_transaction(user_id, 'case_spend', -case['price'], new_balance, f"Открытие кейса: {case['name']}")
        
        roll = random.uniform(0, 100)
        cum = 0
        won_item = None
        for item in case['drop_list']:
            cum += item['chance']
            if roll <= cum:
                won_item = item
                break
        
        new_item_id = database.add_item(user_id, won_item['name'], won_item['price'], won_item['rarity'], won_item.get('image', ''))
        
        database.update_stats(user_id, spent=case['price'], won=won_item['price'], cases=1, spent_cases=case['price'], won_cases=won_item['price'])
        database.add_transaction(user_id, 'case_win', won_item['price'], new_balance + won_item['price'], f"Выбит скин: {won_item['name']}")
        
        database.add_drop_feed(user_id, user_data['display_name'], won_item['name'], won_item['price'], won_item.get('image', ''), case['name'])
    
    return jsonify({
        "success": True,
        "item": won_item,
        "item_id": new_item_id,
        "balance": database.get_user_data(user_id)['balance']
    })

# ---- API (АПГРЕЙД) ----
@app.route('/api/upgrade', methods=['POST'])
def upgrade_item():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Не авторизован"})
    
    user_id = session['user_id']
    data = request.json
    source_item_ids = data.get('source_item_ids', [])
    target_item_name = data.get('target_item_name')
    target_item_price = data.get('target_item_price')
    
    if len(source_item_ids) < 1 or len(source_item_ids) > 6:
        return jsonify({"success": False, "message": "Выберите от 1 до 6 скинов"})
    
    inventory = database.get_inventory(user_id)
    source_items = [i for i in inventory if i['id'] in source_item_ids]
    
    if len(source_items) != len(source_item_ids):
        return jsonify({"success": False, "message": "Некоторые скины не найдены"})
    
    target_item = next((s for s in ALL_ITEMS if s['name'] == target_item_name and s['price'] == target_item_price), None)
    if not target_item:
        return jsonify({"success": False, "message": "Целевой скин не найден"})
    
    current_price = sum(int(i['price']) for i in source_items)
    target_price = int(target_item['price'])
    
    if target_price <= current_price:
        return jsonify({"success": False, "message": "Целевой скин должен быть дороже суммы выбранных"})
    
    raw_chance = (current_price / target_price) * 100
    chance = round(raw_chance, 2)
    
    if chance <= 0:
        return jsonify({"success": False, "message": "Шанс 0.00%! Добавьте больше скинов или выберите более дешевую цель."})
        
    chance = min(chance, 95)
    
    final_roll = random.uniform(0, 100)
    success = final_roll <= chance
    
    with db_lock:
        user_data = database.get_user_data(user_id)
        balance_after = user_data['balance']
        
        if success:
            for item in source_items:
                database.remove_item(user_id, item['id'])
            database.add_item(user_id, f"{target_item['name']} (Апгрейд)", target_price, target_item['rarity'], target_item.get('image', ''))
            message = f"✅ Успех! Ты получил {target_item['name']}!"
            
            database.add_transaction(user_id, 'upgrade_win', target_price, balance_after, f"Апгрейд: {target_item['name']}")
            database.update_stats(user_id, spent=current_price, won=target_price, upgrades=1, spent_upgrades=current_price, won_upgrades=target_price)
            database.add_drop_feed(user_id, user_data['display_name'], target_item['name'], target_price, target_item.get('image', ''), "Апгрейд")
            
        else:
            for item in source_items:
                database.remove_item(user_id, item['id'])
            message = f"💥 Апгрейд провалился! Все выбранные скины сгорели."
            
            database.add_transaction(user_id, 'upgrade_fail', -current_price, balance_after, f"Апгрейд провален")
            database.update_stats(user_id, spent=current_price, won=0, upgrades=1, spent_upgrades=current_price, won_upgrades=0)
    
    return jsonify({
        "success": True,
        "chance": chance,
        "final_roll": final_roll,
        "is_win": success,
        "message": message,
        "balance": database.get_user_data(user_id)['balance'],
        "inventory": database.get_inventory(user_id)
    })

# ---- API (ПРОДАЖА) ----
@app.route('/api/sell_item', methods=['POST'])
def sell_item():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Не авторизован"})
    user_id = session['user_id']
    item_id = request.json.get('item_id')
    
    with db_lock:
        user_data = database.get_user_data(user_id)
        price = database.sell_item(user_id, item_id)
        database.add_transaction(user_id, 'sell', price, user_data['balance'] + price, f"Продажа предмета")
    
    return jsonify({
        "success": True,
        "price": price,
        "balance": database.get_user_data(user_id)['balance']
    })

# ---- API (ПРОДАЖА ВСЕХ) ----
@app.route('/api/sell_all', methods=['POST'])
def sell_all():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Не авторизован"})
    user_id = session['user_id']
    inventory = database.get_inventory(user_id)
    total = 0
    for item in inventory:
        total += database.sell_item(user_id, item['id'])
    return jsonify({
        "success": True,
        "total": total,
        "balance": database.get_user_data(user_id)['balance']
    })

# ---- API (ПОПОЛНЕНИЕ) ----
@app.route('/api/deposit', methods=['POST'])
def deposit():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Не авторизован"})
    user_id = session['user_id']
    data = request.json
    amount = int(data.get('amount', 0))
    
    if amount <= 0:
        return jsonify({"success": False, "message": "Сумма должна быть больше 0"})
    
    with db_lock:
        user_data = database.get_user_data(user_id)
        database.update_balance(user_id, amount)
        database.add_transaction(user_id, 'deposit', amount, user_data['balance'] + amount, "Пополнение баланса")
    
    return jsonify({
        "success": True,
        "balance": database.get_user_data(user_id)['balance']
    })

# ---- API (БАЛАНС) ----
@app.route('/api/balance', methods=['GET'])
def get_balance_api():
    if 'user_id' not in session:
        return jsonify({"balance": 0})
    user_data = database.get_user_data(session['user_id'])
    if not user_data:
        return jsonify({"balance": 0})
    return jsonify({"balance": user_data['balance']})

# ---- API (КОНТРАКТЫ) ----
@app.route('/api/contract', methods=['POST'])
def contract():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Не авторизован"})
    user_id = session['user_id']
    data = request.json
    item_ids = data.get('item_ids', [])
    difficulty = data.get('difficulty', 'medium')
    
    if len(item_ids) < 3 or len(item_ids) > 10:
        return jsonify({"success": False, "message": "От 3 до 10 предметов"})
    
    inventory = database.get_inventory(user_id)
    selected_items = [i for i in inventory if i['id'] in item_ids]
    if len(selected_items) != len(item_ids):
        return jsonify({"success": False, "message": "Некоторые предметы не найдены"})
    
    total_value = sum(i['price'] for i in selected_items)
    
    risk_levels = {
        'easy': {'multiplier': 1.2, 'success_chance': 80},
        'medium': {'multiplier': 1.5, 'success_chance': 50},
        'hard': {'multiplier': 5.0, 'success_chance': 20}
    }
    
    level = risk_levels[difficulty]
    is_success = random.randint(1, 100) <= level['success_chance']
    
    if is_success:
        random_multiplier = random.uniform(0.85, 1.0)
        final_value = total_value * level['multiplier'] * random_multiplier
    else:
        random_multiplier = random.uniform(0.1, 0.6)
        final_value = total_value * random_multiplier
    
    final_value = max(10, round(final_value, 0))
    
    with db_lock:
        user_data = database.get_user_data(user_id)
        balance_after = user_data['balance']
        
        for item_id in item_ids:
            database.remove_item(user_id, item_id)
        
        closest_item = min(ALL_ITEMS, key=lambda x: abs(x['price'] - final_value))
        database.add_item(user_id, closest_item['name'], closest_item['price'], closest_item['rarity'], closest_item.get('image', ''))
        
        message = f"🎉 Ты получил {closest_item['name']} ({closest_item['price']} монет)!"
        if closest_item['price'] < total_value:
            message = f"😔 Ты получил {closest_item['name']} ({closest_item['price']} монет) (не окупилось)"
        
        database.add_transaction(user_id, 'contract', closest_item['price'], balance_after, f"Контракт: {closest_item['name']}")
        database.update_stats(user_id, spent=total_value, won=closest_item['price'], contracts=1, spent_contracts=total_value, won_contracts=closest_item['price'])
        
        database.add_drop_feed(user_id, user_data['display_name'], closest_item['name'], closest_item['price'], closest_item.get('image', ''), "Контракт")
    
    return jsonify({
        "success": True,
        "message": message,
        "old_value": total_value,
        "new_value": closest_item['price'],
        "item": closest_item,
        "balance": database.get_user_data(user_id)['balance'],
        "inventory": database.get_inventory(user_id)
    })

# ---- API (ИСТОРИЯ ТРАНЗАКЦИЙ) ----
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Не авторизован"})
    user_id = session['user_id']
    history = database.get_transactions(user_id, limit=30)
    return jsonify({"success": True, "transactions": history})

# ---- API (ОБНОВЛЕНИЕ ЛЕНТЫ ДРОПА) ----
@app.route('/api/drop_feed_json', methods=['GET'])
def drop_feed_json():
    feed = database.get_drop_feed(15)
    bg_colors = ['#2a1a2a', '#1a2a3a', '#3a1a1a', '#1a3a2a', '#2a3a1a', '#3a2a1a']
    
    html = ''
    if feed:
        for idx, event in enumerate(feed):
            bg = bg_colors[idx % len(bg_colors)]
            html += f'''
            <div class="feed-item" style="background: {bg};">
                <img src="{event['image'] if event['image'] else 'data:image/svg+xml;charset=utf-8,%3Csvg xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22 viewBox%3D%220 0 100 100%22%3E%3Crect width%3D%22100%22 height%3D%22100%22 fill%3D%22%23333%22%2F%3E%3Ctext x%3D%2250%22 y%3D%2250%22 fill%3D%22%23fff%22 font-size%3D%2230%22 text-anchor%3D%22middle%22 dominant-baseline%3D%22middle%22%3E%3F%3C%2Ftext%3E%3C%2Fsvg%3E'}" class="item-icon">
                <div class="item-info">
                    <span class="name">{event['item']}</span>
                    <span class="case-name">из {event['case']}</span>
                </div>
            </div>
            '''
    else:
        html = '<div style="padding: 20px; text-align: center; color: #8899aa; font-size: 13px;">Пока нет дропов...</div>'
    
    return jsonify({"success": True, "html": html})

if __name__ == '__main__':
    app.run(debug=True)
