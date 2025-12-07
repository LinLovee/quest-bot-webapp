# -*- coding: utf-8 -*-
"""
RuneQuestRPG Web App v2.0 - Полностью переработанный бот
Архитектура:
- Классы с наследованием
- Предметы привязаны к классам
- Система кулдауна для навыков
- Правильная работа с БД
- Система инвентаря
"""

import os
import sqlite3
import random
import logging
import json
import time
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
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
    raise ValueError("❌ BOT_TOKEN не найден в .env")

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

# ===================== CLASSES & DATA =====================

class GameClass:
    """Базовый класс персонажа"""
    def __init__(self, name: str, emoji: str, description: str,
                 health: int, mana: int, attack: int, defense: int,
                 crit_chance: float, dodge_chance: float, gold: int):
        self.name = name
        self.emoji = emoji
        self.description = description
        self.health = health
        self.mana = mana
        self.attack = attack
        self.defense = defense
        self.crit_chance = crit_chance
        self.dodge_chance = dodge_chance
        self.gold = gold
        self.skill_name = ""
        self.skill_cooldown = 0  # В секундах
        self.skill_mana_cost = 0

    def get_skill_damage(self, base_damage: float) -> float:
        return base_damage * 1.5

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "emoji": self.emoji,
            "description": self.description,
            "health": self.health,
            "mana": self.mana,
            "attack": self.attack,
            "defense": self.defense,
            "crit_chance": self.crit_chance,
            "dodge_chance": self.dodge_chance,
            "gold": self.gold,
            "skill_name": self.skill_name
        }


class Warrior(GameClass):
    def __init__(self):
        super().__init__(
            name="Воин",
            emoji="⚔️",
            description="Мощный танк ближнего боя",
            health=180,
            mana=40,
            attack=20,
            defense=12,
            crit_chance=8,
            dodge_chance=3,
            gold=150
        )
        self.skill_name = "Мощный удар"
        self.skill_cooldown = 30
        self.skill_mana_cost = 25


class Mage(GameClass):
    def __init__(self):
        super().__init__(
            name="Маг",
            emoji="🧙",
            description="Магия и контроль боя",
            health=80,
            mana=180,
            attack=10,
            defense=4,
            crit_chance=12,
            dodge_chance=2,
            gold=200
        )
        self.skill_name = "Магический взрыв"
        self.skill_cooldown = 25
        self.skill_mana_cost = 35


class Rogue(GameClass):
    def __init__(self):
        super().__init__(
            name="Разбойник",
            emoji="🐱",
            description="Криты и уклонения",
            health=110,
            mana=70,
            attack=24,
            defense=6,
            crit_chance=32,
            dodge_chance=18,
            gold=180
        )
        self.skill_name = "Комбо ударов"
        self.skill_cooldown = 20
        self.skill_mana_cost = 20


class Paladin(GameClass):
    def __init__(self):
        super().__init__(
            name="Паладин",
            emoji="✨",
            description="Святой танк с щитом",
            health=200,
            mana=120,
            attack=16,
            defense=20,
            crit_chance=5,
            dodge_chance=5,
            gold=170
        )
        self.skill_name = "Святой щит"
        self.skill_cooldown = 35
        self.skill_mana_cost = 30


class Archer(GameClass):
    def __init__(self):
        super().__init__(
            name="Лучник",
            emoji="🏹",
            description="Точность и дальний урон",
            health=120,
            mana=60,
            attack=22,
            defense=7,
            crit_chance=28,
            dodge_chance=12,
            gold=160
        )
        self.skill_name = "Град стрел"
        self.skill_cooldown = 22
        self.skill_mana_cost = 28


CLASSES_MAP = {
    "warrior": Warrior(),
    "mage": Mage(),
    "rogue": Rogue(),
    "paladin": Paladin(),
    "archer": Archer()
}

# Предметы привязаны к классам
CLASS_ITEMS = {
    "warrior": [
        {"id": "great_sword", "name": "Великий меч", "emoji": "⚔️", "attack": 8, "price": 100},
        {"id": "steel_armor", "name": "Стальная броня", "emoji": "🛡️", "defense": 10, "price": 120},
        {"id": "health_potion", "name": "Зелье здоровья", "emoji": "🧪", "heal": 50, "price": 30},
    ],
    "mage": [
        {"id": "staff", "name": "Посох магии", "emoji": "🪄", "attack": 5, "mana_regen": 5, "price": 110},
        {"id": "robe", "name": "Магическая мантия", "emoji": "👔", "defense": 6, "mana_regen": 3, "price": 100},
        {"id": "mana_potion", "name": "Зелье маны", "emoji": "💎", "mana": 50, "price": 40},
    ],
    "rogue": [
        {"id": "dagger", "name": "Кинжал ассасина", "emoji": "🗡️", "attack": 10, "crit": 10, "price": 90},
        {"id": "shadow_cloak", "name": "Плащ теней", "emoji": "🧤", "defense": 5, "dodge": 8, "price": 95},
        {"id": "poison_flask", "name": "Флакон яда", "emoji": "☠️", "damage": 25, "price": 50},
    ],
    "paladin": [
        {"id": "holy_sword", "name": "Святой меч", "emoji": "⚔️", "attack": 7, "holy_damage": 5, "price": 105},
        {"id": "divine_shield", "name": "Божественный щит", "emoji": "🛡️", "defense": 15, "price": 140},
        {"id": "blessing_orb", "name": "Сфера благословения", "emoji": "✨", "heal": 30, "defense": 2, "price": 60},
    ],
    "archer": [
        {"id": "longbow", "name": "Длинный лук", "emoji": "🏹", "attack": 9, "crit": 12, "price": 105},
        {"id": "leather_armor", "name": "Кожаная броня", "emoji": "🧥", "defense": 8, "dodge": 5, "price": 85},
        {"id": "arrow_pack", "name": "Колчан стрел", "emoji": "🪶", "attack": 3, "ammo": 20, "price": 35},
    ]
}

ENEMIES = {
    "goblin": {"name": "Гоблин", "emoji": "👹", "hp": 30, "damage": 8, "gold": 50, "exp": 30},
    "orc": {"name": "Орк", "emoji": "👺", "hp": 50, "damage": 14, "gold": 100, "exp": 60},
    "skeleton": {"name": "Скелет", "emoji": "☠️", "hp": 35, "damage": 10, "gold": 75, "exp": 45},
    "troll": {"name": "Тролль", "emoji": "👹", "hp": 70, "damage": 18, "gold": 150, "exp": 85},
    "vampire": {"name": "Вампир", "emoji": "🧛", "hp": 60, "damage": 16, "gold": 130, "exp": 75},
    "witch": {"name": "Ведьма", "emoji": "🧙‍♀️", "hp": 45, "damage": 20, "gold": 120, "exp": 70},
    "werewolf": {"name": "Оборотень", "emoji": "🐺", "hp": 65, "damage": 19, "gold": 140, "exp": 80},
    "dragon": {"name": "Дракон", "emoji": "🐉", "hp": 150, "damage": 30, "gold": 500, "exp": 300}
}

# ===================== DATABASE =====================

def init_db():
    """Инициализация БД с правильной схемой"""
    conn = sqlite3.connect('runequestrpg.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            class TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            experience INTEGER DEFAULT 0,
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
            total_kills INTEGER DEFAULT 0,
            total_damage INTEGER DEFAULT 0,
            skill_last_used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            last_played TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ===================== PLAYER MANAGEMENT =====================

class Player:
    """Класс для управления игроком"""
    
    def __init__(self, user_id: int, game_class: GameClass):
        self.user_id = user_id
        self.class_type = game_class
        self.level = 1
        self.experience = 0
        self.health = game_class.health
        self.max_health = game_class.health
        self.mana = game_class.mana
        self.max_mana = game_class.mana
        self.attack = game_class.attack
        self.defense = game_class.defense
        self.crit_chance = game_class.crit_chance
        self.dodge_chance = game_class.dodge_chance
        self.gold = game_class.gold
        self.inventory = {}
        self.total_kills = 0
        self.total_damage = 0
        self.skill_last_used = 0

    def can_use_skill(self) -> bool:
        """Проверка, готов ли навык к использованию"""
        cooldown = self.class_type.skill_cooldown
        return (time.time() - self.skill_last_used) >= cooldown

    def get_skill_cooldown_remaining(self) -> int:
        """Получить оставшееся время кулдауна в секундах"""
        cooldown = self.class_type.skill_cooldown
        elapsed = int(time.time() - self.skill_last_used)
        remaining = max(0, cooldown - elapsed)
        return remaining

    def use_skill(self):
        """Использовать навык - установить кулдаун"""
        self.skill_last_used = time.time()

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "class": self.class_type.name,
            "level": self.level,
            "experience": self.experience,
            "health": self.health,
            "max_health": self.max_health,
            "mana": self.mana,
            "max_mana": self.max_mana,
            "attack": self.attack,
            "defense": self.defense,
            "crit_chance": self.crit_chance,
            "dodge_chance": self.dodge_chance,
            "gold": self.gold,
            "inventory": self.inventory,
            "total_kills": self.total_kills,
            "total_damage": self.total_damage,
            "skill_cooldown_remaining": self.get_skill_cooldown_remaining()
        }


def get_player_from_db(user_id: int) -> Optional[Player]:
    """Получить игрока из БД"""
    conn = sqlite3.connect('runequestrpg.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    game_class = CLASSES_MAP.get(row['class'])
    if not game_class:
        return None
    
    player = Player(user_id, game_class)
    player.level = row['level']
    player.experience = row['experience']
    player.health = row['health']
    player.max_health = row['max_health']
    player.mana = row['mana']
    player.max_mana = row['max_mana']
    player.attack = row['attack']
    player.defense = row['defense']
    player.crit_chance = row['crit_chance']
    player.dodge_chance = row['dodge_chance']
    player.gold = row['gold']
    player.inventory = json.loads(row['inventory']) if row['inventory'] else {}
    player.total_kills = row['total_kills']
    player.total_damage = row['total_damage']
    player.skill_last_used = row['skill_last_used']
    
    return player


def save_player_to_db(player: Player):
    """Сохранить игрока в БД"""
    conn = sqlite3.connect('runequestrpg.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO players 
        (user_id, class, level, experience, health, max_health, mana, max_mana,
         attack, defense, crit_chance, dodge_chance, gold, inventory, 
         total_kills, total_damage, skill_last_used, created_at, last_played)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        player.user_id,
        player.class_type.name.lower() if hasattr(player.class_type, 'name') else 'warrior',
        player.level,
        player.experience,
        player.health,
        player.max_health,
        player.mana,
        player.max_mana,
        player.attack,
        player.defense,
        player.crit_chance,
        player.dodge_chance,
        player.gold,
        json.dumps(player.inventory),
        player.total_kills,
        player.total_damage,
        player.skill_last_used,
        datetime.now().isoformat(),
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()


# ===================== FLASK APP =====================

app = Flask(__name__, template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/classes')
def get_classes():
    result = {}
    for key, game_class in CLASSES_MAP.items():
        result[key] = game_class.to_dict()
    return jsonify(result)

@app.route('/api/items')
def get_items():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    
    player = get_player_from_db(user_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    # Получить класс игрока и вернуть предметы для этого класса
    class_key = None
    for key, game_class in CLASSES_MAP.items():
        if game_class.name == player.class_type.name:
            class_key = key
            break
    
    if not class_key:
        return jsonify({"error": "Unknown class"}), 400
    
    items = CLASS_ITEMS.get(class_key, [])
    return jsonify({"items": items})

@app.route('/api/player')
def get_player_api():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    
    player = get_player_from_db(user_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    return jsonify(player.to_dict())

@app.route('/api/create', methods=['POST'])
def create_player():
    data = request.json
    user_id = data.get('user_id')
    class_name = data.get('class')
    
    if not user_id or not class_name:
        return jsonify({"error": "Invalid data"}), 400
    
    # Проверить, есть ли уже такой игрок
    existing_player = get_player_from_db(user_id)
    if existing_player:
        return jsonify({"error": "Player already exists"}), 409
    
    # Найти класс
    game_class = CLASSES_MAP.get(class_name)
    if not game_class:
        return jsonify({"error": "Invalid class"}), 400
    
    # Создать нового игрока
    player = Player(user_id, game_class)
    save_player_to_db(player)
    
    return jsonify({"status": "success", "player": player.to_dict()})

@app.route('/api/enemies')
def get_enemies():
    return jsonify(ENEMIES)

@app.route('/api/attack', methods=['POST'])
def attack():
    data = request.json
    user_id = data.get('user_id')
    enemy_type = data.get('enemy_type', 'goblin')
    is_skill = data.get('is_skill', False)
    
    player = get_player_from_db(user_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    enemy = ENEMIES.get(enemy_type)
    if not enemy:
        return jsonify({"error": "Enemy not found"}), 404
    
    # Расчет урона
    if is_skill:
        if not player.can_use_skill():
            cooldown = player.get_skill_cooldown_remaining()
            return jsonify({"error": f"Skill on cooldown: {cooldown}s"}), 400
        
        if player.mana < player.class_type.skill_mana_cost:
            return jsonify({"error": "Not enough mana"}), 400
        
        damage = (player.attack + player.class_type.skill_mana_cost / 2) * 1.5
        player.mana -= player.class_type.skill_mana_cost
        player.use_skill()
        is_crit = True  # Навыки всегда критические
    else:
        base_damage = player.attack + random.uniform(-2, 5)
        is_crit = random.random() < (player.crit_chance / 100)
        damage = base_damage * 1.8 if is_crit else base_damage
    
    player.total_damage += int(damage)
    save_player_to_db(player)
    
    return jsonify({
        "damage": int(damage),
        "is_crit": is_crit,
        "remaining_mana": player.mana
    })

@app.route('/api/leaderboard')
def get_leaderboard():
    conn = sqlite3.connect('runequestrpg.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, class, level, experience, gold, total_kills 
        FROM players 
        ORDER BY level DESC, experience DESC 
        LIMIT 10
    ''')
    
    leaders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(leaders)

# ===================== TELEGRAM BOT =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    
    # Проверить, есть ли уже персонаж
    player = get_player_from_db(user_id)
    
    if player:
        message = f"👋 Добро пожаловать, {username}!\n\n🎮 Ты уже выбрал класс: {player.class_type.name}"
    else:
        message = f"👋 Добро пожаловать, {username}!\n\n🎮 RuneQuestRPG - эпическая RPG в Telegram!"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 ОТКРЫТЬ ИГРУ", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    await update.message.reply_text(message, reply_markup=keyboard)

if __name__ == '__main__':
    logger.info(f"🚀 Flask запущен на 0.0.0.0:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
