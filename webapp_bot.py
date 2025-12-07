# -*- coding: utf-8 -*-
"""
RuneQuestRPG v4.0 - Complete Rewrite with Enhanced Systems
Advanced Combat, Shop System, Leveling, Skills, and Equipment
"""

import os
import sqlite3
import random
import logging
import json
import time
import math
from typing import Optional, Dict, Any, List, Tuple
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

# ===================== GAME CONSTANTS & DATA =====================

LEVEL_UP_EXP = 150  # EXP required per level
BASE_STAT_MULTIPLIER = 1.1  # Stats multiplier per level

CLASSES = {
    "warrior": {
        "name": "Warrior",
        "emoji": "⚔️",
        "description": "Strong melee fighter",
        "health": 250,
        "mana": 60,
        "attack": 24,
        "defense": 18,
        "crit_chance": 10,
        "dodge_chance": 5,
        "crit_damage": 1.5,
        "starting_gold": 200,
        "skills": {
            "power_strike": {
                "name": "Power Strike",
                "emoji": "⚡",
                "cooldown": 30,
                "mana_cost": 25,
                "damage_multiplier": 1.8,
                "description": "Deal massive damage"
            },
            "shield_bash": {
                "name": "Shield Bash",
                "emoji": "🛡️",
                "cooldown": 25,
                "mana_cost": 20,
                "damage_multiplier": 1.3,
                "defense_boost": 10,
                "description": "Damage and boost defense"
            }
        }
    },
    "mage": {
        "name": "Mage",
        "emoji": "🧙",
        "description": "Master of magic",
        "health": 120,
        "mana": 280,
        "attack": 14,
        "defense": 7,
        "crit_chance": 20,
        "dodge_chance": 3,
        "crit_damage": 1.8,
        "starting_gold": 250,
        "skills": {
            "fireball": {
                "name": "Fireball",
                "emoji": "🔥",
                "cooldown": 25,
                "mana_cost": 45,
                "damage_multiplier": 2.2,
                "description": "Explosive fire damage"
            },
            "ice_shield": {
                "name": "Ice Shield",
                "emoji": "❄️",
                "cooldown": 30,
                "mana_cost": 35,
                "damage_multiplier": 0.8,
                "defense_boost": 15,
                "description": "Magical defense shield"
            }
        }
    },
    "rogue": {
        "name": "Rogue",
        "emoji": "🐱",
        "description": "Swift and deadly",
        "health": 160,
        "mana": 100,
        "attack": 28,
        "defense": 10,
        "crit_chance": 45,
        "dodge_chance": 25,
        "crit_damage": 2.2,
        "starting_gold": 220,
        "skills": {
            "backstab": {
                "name": "Backstab",
                "emoji": "🗡️",
                "cooldown": 20,
                "mana_cost": 20,
                "damage_multiplier": 2.5,
                "crit_boost": 25,
                "description": "High critical strike"
            },
            "shadow_step": {
                "name": "Shadow Step",
                "emoji": "👻",
                "cooldown": 22,
                "mana_cost": 15,
                "damage_multiplier": 0.5,
                "dodge_boost": 40,
                "description": "Dodge and counter"
            }
        }
    },
    "paladin": {
        "name": "Paladin",
        "emoji": "✨",
        "description": "Holy defender",
        "health": 280,
        "mana": 180,
        "attack": 20,
        "defense": 26,
        "crit_chance": 8,
        "dodge_chance": 7,
        "crit_damage": 1.6,
        "starting_gold": 230,
        "skills": {
            "divine_shield": {
                "name": "Divine Shield",
                "emoji": "🛡️",
                "cooldown": 35,
                "mana_cost": 40,
                "damage_multiplier": 0.6,
                "defense_boost": 25,
                "heal": 50,
                "description": "Defend and heal"
            },
            "holy_strike": {
                "name": "Holy Strike",
                "emoji": "⚔️",
                "cooldown": 28,
                "mana_cost": 30,
                "damage_multiplier": 1.9,
                "heal": 30,
                "description": "Damage and heal"
            }
        }
    },
    "archer": {
        "name": "Archer",
        "emoji": "🏹",
        "description": "Precision shooter",
        "health": 180,
        "mana": 100,
        "attack": 26,
        "defense": 12,
        "crit_chance": 40,
        "dodge_chance": 18,
        "crit_damage": 2.0,
        "starting_gold": 210,
        "skills": {
            "barrage": {
                "name": "Barrage",
                "emoji": "🎯",
                "cooldown": 23,
                "mana_cost": 30,
                "damage_multiplier": 1.7,
                "hits": 3,
                "description": "Multiple shots"
            },
            "piercing_shot": {
                "name": "Piercing Shot",
                "emoji": "🏹",
                "cooldown": 25,
                "mana_cost": 25,
                "damage_multiplier": 2.1,
                "armor_penetration": 0.5,
                "description": "Ignore defense"
            }
        }
    }
}

ENEMIES = {
    "goblin": {
        "name": "Goblin",
        "emoji": "👹",
        "hp": 35,
        "damage": 10,
        "defense": 3,
        "gold": 60,
        "exp": 40,
        "level": 1,
        "skills": ["attack"]
    },
    "orc": {
        "name": "Orc",
        "emoji": "👺",
        "hp": 70,
        "damage": 18,
        "defense": 6,
        "gold": 120,
        "exp": 80,
        "level": 2,
        "skills": ["attack", "power_hit"]
    },
    "skeleton": {
        "name": "Skeleton",
        "emoji": "☠️",
        "hp": 50,
        "damage": 13,
        "defense": 4,
        "gold": 100,
        "exp": 65,
        "level": 2,
        "skills": ["attack", "bone_throw"]
    },
    "troll": {
        "name": "Troll",
        "emoji": "👹",
        "hp": 120,
        "damage": 22,
        "defense": 10,
        "gold": 200,
        "exp": 130,
        "level": 3,
        "skills": ["attack", "smash", "regenerate"]
    },
    "vampire": {
        "name": "Vampire",
        "emoji": "🧛",
        "hp": 90,
        "damage": 20,
        "defense": 8,
        "gold": 180,
        "exp": 110,
        "level": 3,
        "skills": ["attack", "bite", "drain"]
    },
    "witch": {
        "name": "Witch",
        "emoji": "🧙‍♀️",
        "hp": 75,
        "damage": 24,
        "defense": 5,
        "gold": 160,
        "exp": 95,
        "level": 3,
        "skills": ["attack", "curse", "fireball"]
    },
    "werewolf": {
        "name": "Werewolf",
        "emoji": "🐺",
        "hp": 100,
        "damage": 23,
        "defense": 9,
        "gold": 190,
        "exp": 120,
        "level": 3,
        "skills": ["attack", "bite", "howl"]
    },
    "demon": {
        "name": "Demon",
        "emoji": "😈",
        "hp": 150,
        "damage": 28,
        "defense": 12,
        "gold": 280,
        "exp": 180,
        "level": 4,
        "skills": ["attack", "inferno", "curse"]
    },
    "dragon": {
        "name": "Dragon",
        "emoji": "🐉",
        "hp": 250,
        "damage": 40,
        "defense": 20,
        "gold": 600,
        "exp": 400,
        "level": 5,
        "skills": ["attack", "breath", "tail_swipe", "regenerate"]
    }
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
                crit_damage REAL NOT NULL,
                gold INTEGER NOT NULL,
                inventory TEXT DEFAULT '{}',
                equipment TEXT DEFAULT '{}',
                kills INTEGER DEFAULT 0,
                battles_won INTEGER DEFAULT 0,
                damage_dealt INTEGER DEFAULT 0,
                total_exp INTEGER DEFAULT 0,
                skill_cooldowns TEXT DEFAULT '{}',
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
            now = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO players (user_id, class_type, level, exp, health, max_health, mana, max_mana,
                                   attack, defense, crit_chance, dodge_chance, crit_damage, gold,
                                   inventory, equipment, skill_cooldowns, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                class_type,
                1,
                0,
                cls['health'],
                cls['health'],
                cls['mana'],
                cls['mana'],
                cls['attack'],
                cls['defense'],
                cls['crit_chance'],
                cls['dodge_chance'],
                cls['crit_damage'],
                cls['starting_gold'],
                json.dumps({}),
                json.dumps({}),
                json.dumps({}),
                now,
                now
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
        return player

    @staticmethod
    def save_player(user_id: int, data: Dict):
        conn = sqlite3.connect('runequestrpg.db')
        cursor = conn.cursor()
        
        inventory = data.get('inventory', {})
        equipment = data.get('equipment', {})
        skill_cooldowns = data.get('skill_cooldowns', {})
        
        cursor.execute('''
            UPDATE players SET health = ?, mana = ?, gold = ?, exp = ?, level = ?,
                            damage_dealt = ?, kills = ?, battles_won = ?, total_exp = ?,
                            attack = ?, defense = ?, crit_chance = ?, dodge_chance = ?,
                            inventory = ?, equipment = ?, skill_cooldowns = ?, updated_at = ?
            WHERE user_id = ?
        ''', (
            data.get('health', 0),
            data.get('mana', 0),
            data.get('gold', 0),
            data.get('exp', 0),
            data.get('level', 1),
            data.get('damage_dealt', 0),
            data.get('kills', 0),
            data.get('battles_won', 0),
            data.get('total_exp', 0),
            data.get('attack', 0),
            data.get('defense', 0),
            data.get('crit_chance', 0),
            data.get('dodge_chance', 0),
            json.dumps(inventory),
            json.dumps(equipment),
            json.dumps(skill_cooldowns),
            datetime.now().isoformat(),
            user_id
        ))
        conn.commit()
        conn.close()

    @staticmethod
    def log_battle(user_id: int, enemy_name: str, won: bool, damage_dealt: int, damage_taken: int, duration: int):
        conn = sqlite3.connect('runequestrpg.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO battles (user_id, enemy_name, won, damage_dealt, damage_taken, battle_date, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, enemy_name, won, damage_dealt, damage_taken, datetime.now().isoformat(), duration))
        conn.commit()
        conn.close()

Database.init()

# ===================== COMBAT SYSTEM =====================

class CombatSystem:
    @staticmethod
    def calculate_damage(attacker: Dict, defender: Dict, is_skill: bool = False, skill_data: Dict = None) -> Dict:
        base_damage = attacker.get('attack', 10) + random.uniform(-2, 4)
        
        if is_skill and skill_data:
            base_damage *= skill_data.get('damage_multiplier', 1.0)
        
        crit_chance = attacker.get('crit_chance', 5) / 100
        is_crit = random.random() < crit_chance
        
        if is_crit:
            base_damage *= attacker.get('crit_damage', 1.5)
        
        defense = defender.get('defense', 0) * 0.5
        final_damage = max(1, int(base_damage - defense))
        
        return {
            'damage': final_damage,
            'is_crit': is_crit,
            'base_damage': int(base_damage)
        }
    
    @staticmethod
    def calculate_dodge(defender: Dict) -> bool:
        dodge_chance = defender.get('dodge_chance', 0) / 100
        return random.random() < dodge_chance
    
    @staticmethod
    def apply_equipment_bonuses(player: Dict) -> Dict:
        equipment = player.get('equipment', {})
        bonuses = {'attack': 0, 'defense': 0, 'crit': 0, 'dodge': 0, 'mana_regen': 0}
        
        for slot, item_id in equipment.items():
            for category in ITEMS.values():
                for item in category:
                    if item['id'] == item_id:
                        bonuses['attack'] += item.get('attack', 0)
                        bonuses['defense'] += item.get('defense', 0)
                        bonuses['crit'] += item.get('crit', 0)
                        bonuses['dodge'] += item.get('dodge', 0)
                        bonuses['mana_regen'] += item.get('mana_regen', 0)
        
        player['attack'] += bonuses['attack']
        player['defense'] += bonuses['defense']
        player['crit_chance'] += bonuses['crit']
        player['dodge_chance'] += bonuses['dodge']
        
        return player

# ===================== LEVELING SYSTEM =====================

class LevelingSystem:
    @staticmethod
    def check_level_up(player: Dict) -> Tuple[bool, Dict]:
        exp_needed = LEVEL_UP_EXP * player['level']
        
        if player['exp'] >= exp_needed:
            player['level'] += 1
            player['exp'] -= exp_needed
            
            # Stat increase on level up
            cls = CLASSES[player['class_type']]
            multiplier = BASE_STAT_MULTIPLIER
            
            player['max_health'] = int(player['max_health'] * multiplier)
            player['max_mana'] = int(player['max_mana'] * multiplier)
            player['health'] = player['max_health']
            player['mana'] = player['max_mana']
            player['attack'] = int(player['attack'] * multiplier)
            player['defense'] = int(player['defense'] * multiplier)
            
            return True, {
                'new_level': player['level'],
                'health_increase': int(player['max_health'] - player['max_health'] / multiplier),
                'attack_increase': int(player['attack'] - player['attack'] / multiplier)
            }
        
        return False, {}

# ===================== SHOP SYSTEM =====================

class ShopSystem:
    @staticmethod
    def get_all_items() -> Dict:
        return ITEMS
    
    @staticmethod
    def buy_item(player: Dict, item_id: str) -> Tuple[bool, str]:
        item = None
        for category in ITEMS.values():
            for it in category:
                if it['id'] == item_id:
                    item = it
                    break
        
        if not item:
            return False, "Item not found"
        
        if player['level'] < item.get('level_req', 0):
            return False, f"Need level {item['level_req']}"
        
        if player['gold'] < item['price']:
            return False, "Not enough gold"
        
        player['gold'] -= item['price']
        inventory = player.get('inventory', {})
        
        if item_id not in inventory:
            inventory[item_id] = 0
        inventory[item_id] += 1
        
        player['inventory'] = inventory
        return True, f"Bought {item['name']}"
    
    @staticmethod
    def equip_item(player: Dict, item_id: str) -> Tuple[bool, str]:
        item = None
        for category in ITEMS.values():
            for it in category:
                if it['id'] == item_id:
                    item = it
                    break
        
        if not item:
            return False, "Item not found"
        
        inventory = player.get('inventory', {})
        if inventory.get(item_id, 0) <= 0:
            return False, "Item not in inventory"
        
        # Determine slot
        if 'attack' in item:
            slot = 'weapon'
        elif 'defense' in item:
            slot = 'armor'
        else:
            slot = 'accessory'
        
        equipment = player.get('equipment', {})
        equipment[slot] = item_id
        player['equipment'] = equipment
        
        return True, f"Equipped {item['name']}"

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
    
    player = CombatSystem.apply_equipment_bonuses(player)
    return jsonify(player)

@app.route('/api/items', methods=['GET'])
def get_items():
    items = ShopSystem.get_all_items()
    return jsonify(items)

@app.route('/api/buy-item', methods=['POST'])
def buy_item():
    data = request.json
    user_id = data.get('user_id')
    item_id = data.get('item_id')
    
    player = Database.get_player(user_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    success, message = ShopSystem.buy_item(player, item_id)
    
    if success:
        Database.save_player(user_id, player)
        return jsonify({'success': True, 'message': message, 'gold': player['gold']})
    
    return jsonify({'error': message}), 400

@app.route('/api/equip-item', methods=['POST'])
def equip_item():
    data = request.json
    user_id = data.get('user_id')
    item_id = data.get('item_id')
    
    player = Database.get_player(user_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    success, message = ShopSystem.equip_item(player, item_id)
    
    if success:
        Database.save_player(user_id, player)
        return jsonify({'success': True, 'message': message})
    
    return jsonify({'error': message}), 400

@app.route('/api/enemies', methods=['GET'])
def get_enemies():
    return jsonify(ENEMIES)

@app.route('/api/attack', methods=['POST'])
def attack():
    data = request.json
    user_id = data.get('user_id')
    is_skill = data.get('is_skill', False)
    skill_name = data.get('skill_name')
    
    player = Database.get_player(user_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404
    
    player = CombatSystem.apply_equipment_bonuses(player)
    cls = CLASSES[player['class_type']]
    
    skill_data = None
    if is_skill and skill_name and skill_name in cls.get('skills', {}):
        skill_data = cls['skills'][skill_name]
        cooldowns = player.get('skill_cooldowns', {})
        current_time = time.time()
        
        if cooldowns.get(skill_name, 0) > current_time:
            remaining = int(cooldowns[skill_name] - current_time)
            return jsonify({'error': f'Cooldown: {remaining}s'}), 400
        
        if player['mana'] < skill_data['mana_cost']:
            return jsonify({'error': 'Not enough mana'}), 400
        
        player['mana'] -= skill_data['mana_cost']
        player['skill_cooldowns'][skill_name] = current_time + skill_data['cooldown']
    
    damage_result = CombatSystem.calculate_damage(player, {'defense': 5}, is_skill, skill_data)
    
    Database.save_player(user_id, player)
    
    return jsonify({
        'damage': damage_result['damage'],
        'is_crit': damage_result['is_crit'],
        'mana': player['mana']
    })

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
    duration = data.get('duration', 0)
    
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
    else:
        player['damage_dealt'] += damage_dealt
    
    player['health'] = player['max_health']
    
    # Check for level up
    leveled_up, level_info = LevelingSystem.check_level_up(player)
    
    Database.save_player(user_id, player)
    Database.log_battle(user_id, enemy_name, won, damage_dealt, damage_taken, duration)
    
    return jsonify({
        'success': True,
        'level_up': leveled_up,
        'level_info': level_info if leveled_up else None
    })

@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    conn = sqlite3.connect('runequestrpg.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, class_type, level, total_exp, gold, kills, battles_won, damage_dealt
        FROM players ORDER BY level DESC, total_exp DESC LIMIT 20
    ''')
    leaders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(leaders)

# ===================== TELEGRAM BOT =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    player = Database.get_player(user_id)
    
    msg = f"Hi {name}!\n"
    if player:
        cls = CLASSES[player['class_type']]
        msg += f"Your class: {cls['emoji']} {cls['name']}\nLevel: {player['level']}"
    else:
        msg += "Choose your class and start the adventure!"
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 PLAY", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    await update.message.reply_text(msg, reply_markup=kb)

if __name__ == '__main__':
    logger.info(f"Starting on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
