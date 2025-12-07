# -*- coding: utf-8 -*-
"""
RuneQuestRPG v3.0 - Complete Rewrite
Clean Architecture with Proper Design
"""

import os
import sqlite3
import random
import logging
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# ===================== CONFIG =====================

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://quest-bot-webapp.onrender.com/")
PORT = int(os.getenv("PORT", "5000"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env")

if not os.path.exists("logs"):
    os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/runequestrpg.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("RuneQuestRPG")

# ===================== GAME DATA =====================

CLASSES = {
    "warrior": {
        "name": "Warrior",
        "emoji": "⚔️",
        "description": "Strong melee fighter",
        "health": 200,
        "mana": 50,
        "attack": 22,
        "defense": 15,
        "crit_chance": 8,
        "dodge_chance": 3,
        "starting_gold": 150,
        "skill_name": "Power Strike",
        "skill_cooldown": 30,
        "skill_mana_cost": 25
    },
    "mage": {
        "name": "Mage",
        "emoji": "🧙",
        "description": "Master of magic",
        "health": 90,
        "mana": 200,
        "attack": 12,
        "defense": 5,
        "crit_chance": 15,
        "dodge_chance": 2,
        "starting_gold": 200,
        "skill_name": "Fireball",
        "skill_cooldown": 25,
        "skill_mana_cost": 40
    },
    "rogue": {
        "name": "Rogue",
        "emoji": "🐱",
        "description": "Swift and deadly",
        "health": 130,
        "mana": 80,
        "attack": 26,
        "defense": 8,
        "crit_chance": 35,
        "dodge_chance": 20,
        "starting_gold": 170,
        "skill_name": "Backstab",
        "skill_cooldown": 20,
        "skill_mana_cost": 20
    },
    "paladin": {
        "name": "Paladin",
        "emoji": "✨",
        "description": "Holy defender",
        "health": 220,
        "mana": 140,
        "attack": 18,
        "defense": 22,
        "crit_chance": 5,
        "dodge_chance": 5,
        "starting_gold": 180,
        "skill_name": "Divine Shield",
        "skill_cooldown": 35,
        "skill_mana_cost": 30
    },
    "archer": {
        "name": "Archer",
        "emoji": "🏹",
        "description": "Precision shooter",
        "health": 140,
        "mana": 70,
        "attack": 24,
        "defense": 10,
        "crit_chance": 30,
        "dodge_chance": 15,
        "starting_gold": 160,
        "skill_name": "Barrage",
        "skill_cooldown": 22,
        "skill_mana_cost": 28
    }
}

ENEMIES = {
    "goblin": {"name": "Goblin", "emoji": "👹", "hp": 30, "damage": 8, "gold": 50, "exp": 30},
    "orc": {"name": "Orc", "emoji": "👺", "hp": 50, "damage": 14, "gold": 100, "exp": 60},
    "skeleton": {"name": "Skeleton", "emoji": "☠️", "hp": 40, "damage": 11, "gold": 80, "exp": 50},
    "troll": {"name": "Troll", "emoji": "👹", "hp": 80, "damage": 18, "gold": 150, "exp": 90},
    "vampire": {"name": "Vampire", "emoji": "🧛", "hp": 70, "damage": 16, "gold": 140, "exp": 80},
    "witch": {"name": "Witch", "emoji": "🧙‍♀️", "hp": 55, "damage": 20, "gold": 130, "exp": 75},
    "werewolf": {"name": "Werewolf", "emoji": "🐺", "hp": 75, "damage": 19, "gold": 145, "exp": 85},
    "dragon": {"name": "Dragon", "emoji": "🐉", "hp": 200, "damage": 35, "gold": 500, "exp": 300}
}

CLASS_ITEMS = {
    "warrior": [
        {"id": "sword", "name": "Great Sword", "emoji": "⚔️", "attack": 8, "price": 100},
        {"id": "armor", "name": "Steel Armor", "emoji": "🛡️", "defense": 12, "price": 120},
        {"id": "potion", "name": "Health Potion", "emoji": "🧪", "heal": 50, "price": 30},
    ],
    "mage": [
        {"id": "staff", "name": "Arcane Staff", "emoji": "🎯", "attack": 6, "mana_regen": 5, "price": 110},
        {"id": "robe", "name": "Mystic Robe", "emoji": "👔", "defense": 8, "mana_regen": 3, "price": 100},
        {"id": "mana_pot", "name": "Mana Potion", "emoji": "💎", "mana": 60, "price": 45},
    ],
    "rogue": [
        {"id": "dagger", "name": "Assassin Dagger", "emoji": "⚔️", "attack": 10, "crit": 12, "price": 95},
        {"id": "cloak", "name": "Shadow Cloak", "emoji": "🧥", "defense": 7, "dodge": 10, "price": 105},
        {"id": "poison", "name": "Poison Vial", "emoji": "☠️", "damage": 30, "price": 55},
    ],
    "paladin": [
        {"id": "holy_sword", "name": "Holy Sword", "emoji": "⚔️", "attack": 8, "holy": 6, "price": 110},
        {"id": "holy_shield", "name": "Divine Shield", "emoji": "🛡️", "defense": 18, "price": 150},
        {"id": "blessing", "name": "Blessing Orb", "emoji": "✨", "heal": 35, "defense": 3, "price": 65},
    ],
    "archer": [
        {"id": "longbow", "name": "Longbow", "emoji": "🏹", "attack": 10, "crit": 14, "price": 110},
        {"id": "leather", "name": "Leather Armor", "emoji": "🧥", "defense": 9, "dodge": 7, "price": 90},
        {"id": "arrows", "name": "Arrow Pack", "emoji": "🎯", "attack": 4, "ammo": 20, "price": 40},
    ]
}

# ===================== DATABASE =====================

class Database:
    @staticmethod
    def init():
        conn = sqlite3.connect('runequestrpg.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                class_type TEXT NOT NULL UNIQUE,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                health INTEGER NOT NULL,
                max_health INTEGER NOT NULL,
                mana INTEGER NOT NULL,
                max_mana INTEGER NOT NULL,
                attack INTEGER NOT NULL,
                defense INTEGER NOT NULL,
                crit_chance REAL NOT NULL,
                dodge_chance REAL NOT NULL,
                gold INTEGER NOT NULL,
                inventory TEXT DEFAULT '{}',
                kills INTEGER DEFAULT 0,
                damage INTEGER DEFAULT 0,
                skill_cd REAL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()

    @staticmethod
    def player_exists(user_id: int) -> bool:
        conn = sqlite3.connect('runequestrpg.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM players WHERE user_id = ?', (user_id,))
        result = cursor.fetchone() is not None
        conn.close()
        return result

    @staticmethod
    def create_player(user_id: int, class_type: str) -> bool:
        if Database.player_exists(user_id):
            return False
        
        if class_type not in CLASSES:
            return False
        
        cls = CLASSES[class_type]
        conn = sqlite3.connect('runequestrpg.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO players (user_id, class_type, health, max_health, mana, max_mana,
                                   attack, defense, crit_chance, dodge_chance, gold,
                                   inventory, skill_cd, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                class_type,
                cls['health'],
                cls['health'],
                cls['mana'],
                cls['mana'],
                cls['attack'],
                cls['defense'],
                cls['crit_chance'],
                cls['dodge_chance'],
                cls['starting_gold'],
                '{}',
                0,
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

    @staticmethod
    def get_player(user_id: int) -> Optional[Dict]:
        conn = sqlite3.connect('runequestrpg.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return dict(row)

    @staticmethod
    def save_player(user_id: int, data: Dict):
        conn = sqlite3.connect('runequestrpg.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE players SET health = ?, mana = ?, gold = ?, exp = ?,
                            damage = ?, kills = ?, skill_cd = ?
            WHERE user_id = ?
        ''', (data['health'], data['mana'], data['gold'], data['exp'],
              data['damage'], data['kills'], data['skill_cd'], user_id))
        conn.commit()
        conn.close()

Database.init()

# ===================== FLASK APP =====================

app = Flask(__name__, template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/classes', methods=['GET'])
def get_classes():
    return jsonify(CLASSES)

@app.route('/api/create', methods=['POST'])
def create():
    data = request.json
    user_id = data.get('user_id')
    class_type = data.get('class')
    
    if not user_id or not class_type:
        return jsonify({'error': 'Invalid input'}), 400
    
    if Database.player_exists(user_id):
        return jsonify({'error': 'Player exists'}), 409
    
    if class_type not in CLASSES:
        return jsonify({'error': 'Invalid class'}), 400
    
    if not Database.create_player(user_id, class_type):
        return jsonify({'error': 'Failed to create'}), 500
    
    player = Database.get_player(user_id)
    return jsonify({'success': True, 'player': player}), 201

@app.route('/api/player', methods=['GET'])
def get_player():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    
    player = Database.get_player(user_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    return jsonify(player)

@app.route('/api/items', methods=['GET'])
def get_items():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'Missing user_id'}), 400
    
    player = Database.get_player(user_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    items = CLASS_ITEMS.get(player['class_type'], [])
    return jsonify({'items': items})

@app.route('/api/enemies', methods=['GET'])
def get_enemies():
    return jsonify(ENEMIES)

@app.route('/api/attack', methods=['POST'])
def attack():
    data = request.json
    user_id = data.get('user_id')
    is_skill = data.get('is_skill', False)
    
    player = Database.get_player(user_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    cls = CLASSES[player['class_type']]
    
    # Skill check
    if is_skill:
        current_time = time.time()
        if (current_time - player['skill_cd']) < cls['skill_cooldown']:
            remaining = int(cls['skill_cooldown'] - (current_time - player['skill_cd']))
            return jsonify({'error': f'Skill cooldown: {remaining}s'}), 400
        
        if player['mana'] < cls['skill_mana_cost']:
            return jsonify({'error': 'Not enough mana'}), 400
        
        damage = (player['attack'] + cls['skill_mana_cost'] / 2) * 1.5
        player['mana'] -= cls['skill_mana_cost']
        player['skill_cd'] = current_time
    else:
        base = player['attack'] + random.uniform(-3, 5)
        is_crit = random.random() < (player['crit_chance'] / 100)
        damage = base * 1.8 if is_crit else base
    
    player['damage'] += int(damage)
    Database.save_player(user_id, player)
    
    return jsonify({'damage': int(damage), 'mana': player['mana']})

@app.route('/api/battle-end', methods=['POST'])
def battle_end():
    data = request.json
    user_id = data.get('user_id')
    won = data.get('won', False)
    gold_gain = data.get('gold', 0)
    exp_gain = data.get('exp', 0)
    
    player = Database.get_player(user_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    if won:
        player['gold'] += gold_gain
        player['exp'] += exp_gain
        player['kills'] += 1
    
    player['health'] = player['max_health']
    Database.save_player(user_id, player)
    
    return jsonify({'success': True})

@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    conn = sqlite3.connect('runequestrpg.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, class_type, level, exp, gold, kills FROM players ORDER BY level DESC, exp DESC LIMIT 10')
    leaders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(leaders)

# ===================== TELEGRAM BOT =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    player = Database.get_player(user_id)
    
    msg = f"Hi {name}!\n" + (
        f"Your class: {CLASSES[player['class_type']]['name']}" if player
        else "Choose your class and start the adventure!"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 PLAY", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    await update.message.reply_text(msg, reply_markup=kb)

if __name__ == '__main__':
    logger.info(f"Starting on {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
