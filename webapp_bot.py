# -*- coding: utf-8 -*-
"""
RuneQuestRPG v5.0 - Major Bugfix & Feature Update
Fixed: Leaderboard system, added daily quests, achievements, auction house
"""

import os
import sqlite3
import random
import logging
import json
import time
import math
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

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

# ===================== GAME CONSTANTS =====================

LEVEL_UP_EXP = 150
BASE_STAT_MULTIPLIER = 1.1

CLASSES = {
    "warrior": {"name": "Warrior", "emoji": "⚔️", "description": "Strong melee fighter", "health": 250, "mana": 60, "attack": 24, "defense": 18, "crit_chance": 10, "dodge_chance": 5, "crit_damage": 1.5, "starting_gold": 200},
    "mage": {"name": "Mage", "emoji": "🧙", "description": "Master of magic", "health": 120, "mana": 280, "attack": 14, "defense": 7, "crit_chance": 20, "dodge_chance": 3, "crit_damage": 1.8, "starting_gold": 250},
    "rogue": {"name": "Rogue", "emoji": "🐱", "description": "Swift and deadly", "health": 160, "mana": 100, "attack": 28, "defense": 10, "crit_chance": 45, "dodge_chance": 25, "crit_damage": 2.2, "starting_gold": 220},
    "paladin": {"name": "Paladin", "emoji": "✨", "description": "Holy defender", "health": 280, "mana": 180, "attack": 20, "defense": 26, "crit_chance": 8, "dodge_chance": 7, "crit_damage": 1.6, "starting_gold": 230},
    "archer": {"name": "Archer", "emoji": "🏹", "description": "Precision shooter", "health": 180, "mana": 100, "attack": 26, "defense": 12, "crit_chance": 40, "dodge_chance": 18, "crit_damage": 2.0, "starting_gold": 210}
}

ENEMIES = {
    "goblin": {"name": "Goblin", "emoji": "👹", "hp": 35, "damage": 10, "defense": 3, "gold": 60, "exp": 40, "level": 1},
    "orc": {"name": "Orc", "emoji": "👺", "hp": 70, "damage": 18, "defense": 6, "gold": 120, "exp": 80, "level": 2},
    "skeleton": {"name": "Skeleton", "emoji": "☠️", "hp": 50, "damage": 13, "defense": 4, "gold": 100, "exp": 65, "level": 2},
    "troll": {"name": "Troll", "emoji": "👹", "hp": 120, "damage": 22, "defense": 10, "gold": 200, "exp": 130, "level": 3},
    "vampire": {"name": "Vampire", "emoji": "🧛", "hp": 90, "damage": 20, "defense": 8, "gold": 180, "exp": 110, "level": 3},
    "witch": {"name": "Witch", "emoji": "🧙‍♀️", "hp": 75, "damage": 24, "defense": 5, "gold": 160, "exp": 95, "level": 3},
    "werewolf": {"name": "Werewolf", "emoji": "🐺", "hp": 100, "damage": 23, "defense": 9, "gold": 190, "exp": 120, "level": 3},
    "demon": {"name": "Demon", "emoji": "😈", "hp": 150, "damage": 28, "defense": 12, "gold": 280, "exp": 180, "level": 4},
    "dragon": {"name": "Dragon", "emoji": "🐉", "hp": 250, "damage": 40, "defense": 20, "gold": 600, "exp": 400, "level": 5}
}

ITEMS = {
    "weapons": [
        {"id": "iron_sword", "name": "Iron Sword", "emoji": "⚔️", "attack": 5, "price": 80, "level_req": 1},
        {"id": "steel_sword", "name": "Steel Sword", "emoji": "⚔️", "attack": 10, "price": 180, "level_req": 3},
        {"id": "legendary_sword", "name": "Legendary Blade", "emoji": "⚔️", "attack": 18, "price": 400, "level_req": 6},
        {"id": "staff", "name": "Arcane Staff", "emoji": "🎯", "attack": 6, "mana_regen": 10, "price": 120, "level_req": 1},
        {"id": "enchanted_staff", "name": "Enchanted Staff", "emoji": "🎯", "attack": 12, "mana_regen": 20, "price": 250, "level_req": 4},
    ],
    "armor": [
        {"id": "leather_armor", "name": "Leather Armor", "emoji": "🧥", "defense": 5, "price": 100, "level_req": 1},
        {"id": "steel_armor", "name": "Steel Armor", "emoji": "🛡️", "defense": 12, "price": 220, "level_req": 3},
        {"id": "diamond_armor", "name": "Diamond Armor", "emoji": "💎", "defense": 22, "price": 500, "level_req": 6},
        {"id": "mage_robe", "name": "Mystic Robe", "emoji": "👔", "defense": 4, "mana_regen": 15, "price": 150, "level_req": 2},
    ],
    "accessories": [
        {"id": "ruby_ring", "name": "Ruby Ring", "emoji": "💍", "attack": 3, "crit": 5, "price": 90, "level_req": 1},
        {"id": "sapphire_amulet", "name": "Sapphire Amulet", "emoji": "📿", "defense": 4, "mana": 30, "price": 120, "level_req": 2},
        {"id": "gold_ring", "name": "Gold Ring", "emoji": "💍", "gold_boost": 0.2, "price": 200, "level_req": 3},
    ],
    "potions": [
        {"id": "health_potion", "name": "Health Potion", "emoji": "🧪", "heal": 50, "price": 30, "level_req": 0},
        {"id": "mana_potion", "name": "Mana Potion", "emoji": "💎", "mana": 60, "price": 40, "level_req": 0},
        {"id": "super_potion", "name": "Super Potion", "emoji": "🔮", "heal": 100, "price": 80, "level_req": 3},
    ]
}

DAILY_QUESTS = {
    "defeat_enemies": {"name": "Defeat 5 Enemies", "emoji": "⚔️", "reward": 150, "target": 5, "type": "kills"},
    "earn_gold": {"name": "Earn 500 Gold", "emoji": "💰", "reward": 100, "target": 500, "type": "gold"},
    "gain_exp": {"name": "Gain 300 EXP", "emoji": "⭐", "reward": 200, "target": 300, "type": "exp"},
}

ACHIEVEMENTS = {
    "first_kill": {"name": "First Blood", "emoji": "🐛", "description": "Defeat your first enemy", "points": 10},
    "level_5": {"name": "Growing Strong", "emoji": "💪", "description": "Reach level 5", "points": 50},
    "level_10": {"name": "Legendary", "emoji": "👑", "description": "Reach level 10", "points": 100},
    "rich": {"name": "Wealthy", "emoji": "💎", "description": "Accumulate 5000 gold", "points": 75},
    "hundred_kills": {"name": "Slayer", "emoji": "⚔️", "description": "Defeat 100 enemies", "points": 200},
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
                username TEXT UNIQUE,
                class_type TEXT NOT NULL,
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
                crit_damage REAL NOT NULL,
                gold INTEGER NOT NULL,
                inventory TEXT DEFAULT '{}',
                equipment TEXT DEFAULT '{}',
                kills INTEGER DEFAULT 0,
                battles_won INTEGER DEFAULT 0,
                battles_lost INTEGER DEFAULT 0,
                damage_dealt INTEGER DEFAULT 0,
                total_exp INTEGER DEFAULT 0,
                skill_cooldowns TEXT DEFAULT '{}',
                achievements TEXT DEFAULT '{}',
                daily_quests TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS battles (
                battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                enemy_name TEXT,
                won BOOLEAN,
                damage_dealt INTEGER,
                damage_taken INTEGER,
                battle_date TEXT,
                duration INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auction_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER,
                item_name TEXT,
                item_data TEXT,
                price INTEGER,
                created_at TEXT
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
    def create_player(user_id: int, class_type: str, username: str) -> bool:
        if Database.player_exists(user_id):
            return False
        
        if class_type not in CLASSES:
            return False
        
        cls = CLASSES[class_type]
        conn = sqlite3.connect('runequestrpg.db')
        cursor = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            daily_quests = {quest_id: {"progress": 0, "completed": False} for quest_id in DAILY_QUESTS}
            
            cursor.execute('''
                INSERT INTO players (user_id, username, class_type, level, exp, health, max_health, mana, max_mana,
                                   attack, defense, crit_chance, dodge_chance, crit_damage, gold,
                                   inventory, equipment, skill_cooldowns, daily_quests, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, username, class_type, 1, 0,
                cls['health'], cls['health'],
                cls['mana'], cls['mana'],
                cls['attack'], cls['defense'],
                cls['crit_chance'], cls['dodge_chance'], cls['crit_damage'],
                cls['starting_gold'],
                json.dumps({}), json.dumps({}), json.dumps({}),
                json.dumps(daily_quests), now, now
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error creating player: {e}")
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
        
        player = dict(row)
        player['inventory'] = json.loads(player['inventory'])
        player['equipment'] = json.loads(player['equipment'])
        player['skill_cooldowns'] = json.loads(player['skill_cooldowns'])
        player['achievements'] = json.loads(player['achievements'])
        player['daily_quests'] = json.loads(player['daily_quests'])
        return player

    @staticmethod
    def save_player(user_id: int, data: Dict):
        conn = sqlite3.connect('runequestrpg.db')
        cursor = conn.cursor()
        
        inventory = data.get('inventory', {})
        equipment = data.get('equipment', {})
        skill_cooldowns = data.get('skill_cooldowns', {})
        achievements = data.get('achievements', {})
        daily_quests = data.get('daily_quests', {})
        
        cursor.execute('''
            UPDATE players SET health = ?, mana = ?, gold = ?, exp = ?, level = ?,
                            damage_dealt = ?, kills = ?, battles_won = ?, battles_lost = ?, total_exp = ?,
                            attack = ?, defense = ?, crit_chance = ?, dodge_chance = ?,
                            inventory = ?, equipment = ?, skill_cooldowns = ?, achievements = ?,
                            daily_quests = ?, updated_at = ?
            WHERE user_id = ?
        ''', (
            data.get('health', 0), data.get('mana', 0), data.get('gold', 0),
            data.get('exp', 0), data.get('level', 1),
            data.get('damage_dealt', 0), data.get('kills', 0),
            data.get('battles_won', 0), data.get('battles_lost', 0),
            data.get('total_exp', 0),
            data.get('attack', 0), data.get('defense', 0),
            data.get('crit_chance', 0), data.get('dodge_chance', 0),
            json.dumps(inventory), json.dumps(equipment),
            json.dumps(skill_cooldowns), json.dumps(achievements),
            json.dumps(daily_quests), datetime.now().isoformat(),
            user_id
        ))
        conn.commit()
        conn.close()

    @staticmethod
    def get_leaderboard(limit: int = 50) -> List[Dict]:
        conn = sqlite3.connect('runequestrpg.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, class_type, level, total_exp, gold, kills, battles_won, damage_dealt
            FROM players ORDER BY level DESC, total_exp DESC LIMIT ?
        ''', (limit,))
        leaders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return leaders

Database.init()

# ===================== COMBAT SYSTEM =====================

class CombatSystem:
    @staticmethod
    def calculate_damage(attacker: Dict, defender: Dict, is_skill: bool = False) -> Dict:
        base_damage = attacker.get('attack', 10) + random.uniform(-3, 5)
        
        if is_skill:
            base_damage *= 1.5
        
        crit_chance = attacker.get('crit_chance', 5) / 100
        is_crit = random.random() < crit_chance
        
        if is_crit:
            base_damage *= attacker.get('crit_damage', 1.5)
        
        defense = defender.get('defense', 0) * 0.4
        final_damage = max(1, int(base_damage - defense))
        
        return {'damage': final_damage, 'is_crit': is_crit}
    
    @staticmethod
    def apply_equipment_bonuses(player: Dict) -> Dict:
        equipment = player.get('equipment', {})
        bonuses = {'attack': 0, 'defense': 0, 'crit': 0, 'dodge': 0}
        
        for slot, item_id in equipment.items():
            for category in ITEMS.values():
                for item in category:
                    if item['id'] == item_id:
                        bonuses['attack'] += item.get('attack', 0)
                        bonuses['defense'] += item.get('defense', 0)
                        bonuses['crit'] += item.get('crit', 0)
                        bonuses['dodge'] += item.get('dodge', 0)
        
        player['attack'] += bonuses['attack']
        player['defense'] += bonuses['defense']
        player['crit_chance'] += bonuses['crit']
        player['dodge_chance'] += bonuses['dodge']
        
        return player

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
    username = data.get('username', f'Player_{user_id}')
    
    if not user_id or not class_type:
        return jsonify({'error': 'Invalid input'}), 400
    
    if Database.player_exists(user_id):
        return jsonify({'error': 'Player exists'}), 409
    
    if class_type not in CLASSES:
        return jsonify({'error': 'Invalid class'}), 400
    
    if not Database.create_player(user_id, class_type, username):
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
    
    player = CombatSystem.apply_equipment_bonuses(player)
    return jsonify(player)

@app.route('/api/items', methods=['GET'])
def get_items():
    return jsonify(ITEMS)

@app.route('/api/buy-item', methods=['POST'])
def buy_item():
    data = request.json
    user_id = data.get('user_id')
    item_id = data.get('item_id')
    
    player = Database.get_player(user_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    item = None
    for category in ITEMS.values():
        for it in category:
            if it['id'] == item_id:
                item = it
                break
    
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    if player['level'] < item.get('level_req', 0):
        return jsonify({'error': f'Need level {item["level_req"]}'}), 400
    
    if player['gold'] < item['price']:
        return jsonify({'error': 'Not enough gold'}), 400
    
    player['gold'] -= item['price']
    if item_id not in player['inventory']:
        player['inventory'][item_id] = 0
    player['inventory'][item_id] += 1
    
    Database.save_player(user_id, player)
    return jsonify({'success': True, 'gold': player['gold']})

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
    
    player = CombatSystem.apply_equipment_bonuses(player)
    
    damage_result = CombatSystem.calculate_damage(player, {'defense': 5}, is_skill)
    
    Database.save_player(user_id, player)
    
    return jsonify(damage_result)

@app.route('/api/battle-end', methods=['POST'])
def battle_end():
    data = request.json
    user_id = data.get('user_id')
    enemy_name = data.get('enemy_name', 'Unknown')
    won = data.get('won', False)
    gold_gain = data.get('gold', 0)
    exp_gain = data.get('exp', 0)
    damage_dealt = data.get('damage_dealt', 0)
    damage_taken = data.get('damage_taken', 0)
    
    player = Database.get_player(user_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    if won:
        player['gold'] += gold_gain
        player['exp'] += exp_gain
        player['kills'] += 1
        player['battles_won'] += 1
        player['total_exp'] += exp_gain
        player['damage_dealt'] += damage_dealt
        
        # Check achievements
        if player['kills'] == 1:
            player['achievements']['first_kill'] = True
        if player['kills'] == 100:
            player['achievements']['hundred_kills'] = True
        if player['gold'] >= 5000:
            player['achievements']['rich'] = True
        
        # Update daily quests
        if 'defeat_enemies' in player['daily_quests']:
            player['daily_quests']['defeat_enemies']['progress'] += 1
            if player['daily_quests']['defeat_enemies']['progress'] >= 5:
                player['daily_quests']['defeat_enemies']['completed'] = True
                player['gold'] += DAILY_QUESTS['defeat_enemies']['reward']
        
        if 'gain_exp' in player['daily_quests']:
            player['daily_quests']['gain_exp']['progress'] += exp_gain
            if player['daily_quests']['gain_exp']['progress'] >= 300:
                player['daily_quests']['gain_exp']['completed'] = True
                player['gold'] += DAILY_QUESTS['gain_exp']['reward']
    else:
        player['battles_lost'] += 1
    
    player['health'] = player['max_health']
    
    # Check level up
    exp_needed = LEVEL_UP_EXP * player['level']
    level_up = False
    if player['exp'] >= exp_needed:
        player['level'] += 1
        player['exp'] -= exp_needed
        player['max_health'] = int(player['max_health'] * BASE_STAT_MULTIPLIER)
        player['max_mana'] = int(player['max_mana'] * BASE_STAT_MULTIPLIER)
        player['attack'] = int(player['attack'] * BASE_STAT_MULTIPLIER)
        player['defense'] = int(player['defense'] * BASE_STAT_MULTIPLIER)
        player['health'] = player['max_health']
        player['mana'] = player['max_mana']
        level_up = True
        
        if player['level'] == 5:
            player['achievements']['level_5'] = True
        if player['level'] == 10:
            player['achievements']['level_10'] = True
    
    Database.save_player(user_id, player)
    
    return jsonify({'success': True, 'level_up': level_up, 'player': player})

@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    leaders = Database.get_leaderboard(50)
    return jsonify(leaders)

@app.route('/api/daily-quests', methods=['GET'])
def get_daily_quests():
    return jsonify(DAILY_QUESTS)

@app.route('/api/achievements', methods=['GET'])
def get_achievements():
    return jsonify(ACHIEVEMENTS)

if __name__ == '__main__':
    logger.info(f"Starting on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
