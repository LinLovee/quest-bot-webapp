# -*- coding: utf-8 -*-
"""
RuneQuestRPG Web App — Telegram Bot с Web App версией
Улучшенная версия с новыми функциями и системами
"""

import os
import sqlite3
import random
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from functools import wraps
from enum import Enum
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===================== КОНФИГ =====================

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

MAX_LEVEL = 100
LEVEL_UP_BASE = 100
STATS_PER_LEVEL = {"health": 20, "mana": 15, "attack": 5, "defense": 2}

# ===================== ENUM И КЛАССЫ =====================

class Element(Enum):
    PHYSICAL = "physical"
    FIRE = "fire"
    ICE = "ice"
    SHADOW = "shadow"
    HOLY = "holy"
    POISON = "poison"
    ARCANE = "arcane"

class RuneType(Enum):
    OFFENSIVE = "offensive"
    DEFENSIVE = "defensive"
    UTILITY = "utility"

# ===================== ДАННЫЕ =====================

CLASSES: Dict[str, Dict[str, Any]] = {
    "warrior": {
        "name": "Воин",
        "emoji": "🗡️",
        "description": "Классический боец ближнего боя.",
        "health": 150,
        "mana": 30,
        "attack": 18,
        "defense": 10,
        "crit_chance": 8,
        "starting_gold": 150,
        "spell_power": 0,
        "dodge_chance": 3,
        "element": Element.PHYSICAL.value,
        "special_skill": "Мощный удар"
    },
    "mage": {
        "name": "Маг",
        "emoji": "🪄",
        "description": "Слабое тело, но мощная магия.",
        "health": 80,
        "mana": 160,
        "attack": 10,
        "defense": 4,
        "crit_chance": 12,
        "starting_gold": 200,
        "spell_power": 35,
        "dodge_chance": 2,
        "element": Element.ARCANE.value,
        "special_skill": "Магический взрыв"
    },
    "rogue": {
        "name": "Разбойник",
        "emoji": "🐱",
        "description": "Криты и уклонения - вот его стиль.",
        "health": 100,
        "mana": 60,
        "attack": 22,
        "defense": 6,
        "crit_chance": 28,
        "starting_gold": 180,
        "spell_power": 8,
        "dodge_chance": 15,
        "element": Element.SHADOW.value,
        "special_skill": "Комбо удары"
    },
    "paladin": {
        "name": "Паладин",
        "emoji": "✨",
        "description": "Танк со священной силой.",
        "health": 170,
        "mana": 100,
        "attack": 16,
        "defense": 18,
        "crit_chance": 5,
        "starting_gold": 170,
        "spell_power": 15,
        "dodge_chance": 5,
        "element": Element.HOLY.value,
        "special_skill": "Святой щит"
    },
    "archer": {
        "name": "Лучник",
        "emoji": "🏹",
        "description": "Точность и дальние удары.",
        "health": 110,
        "mana": 50,
        "attack": 20,
        "defense": 7,
        "crit_chance": 25,
        "starting_gold": 160,
        "spell_power": 5,
        "dodge_chance": 10,
        "element": Element.PHYSICAL.value,
        "special_skill": "Град стрел"
    }
}

ENEMIES = {
    "goblin": {"name": "Гоблин", "emoji": "👹", "hp": 25, "damage": 8, "gold": 50, "exp": 30},
    "orc": {"name": "Орк", "emoji": "👺", "hp": 45, "damage": 14, "gold": 100, "exp": 60},
    "skeleton": {"name": "Скелет", "emoji": "☠️", "hp": 30, "damage": 10, "gold": 75, "exp": 40},
    "troll": {"name": "Тролль", "emoji": "👹", "hp": 60, "damage": 18, "gold": 150, "exp": 80},
    "vampire": {"name": "Вампир", "emoji": "🦇", "hp": 50, "damage": 16, "gold": 120, "exp": 70},
    "dragon": {"name": "Дракон", "emoji": "🐉", "hp": 100, "damage": 25, "gold": 300, "exp": 200},
    "witch": {"name": "Ведьма", "emoji": "🧙", "hp": 40, "damage": 20, "gold": 110, "exp": 65},
    "werewolf": {"name": "Оборотень", "emoji": "🐺", "hp": 55, "damage": 19, "gold": 130, "exp": 75}
}

ITEMS = {
    "sword": {"name": "Мечь", "emoji": "⚔️", "attack": 5, "price": 50},
    "shield": {"name": "Щит", "emoji": "🛡️", "defense": 5, "price": 40},
    "potion": {"name": "Зелье здоровья", "emoji": "🧪", "heal": 30, "price": 25},
    "mana_potion": {"name": "Зелье маны", "emoji": "💎", "mana": 30, "price": 30},
    "armor": {"name": "Броня", "emoji": "🛡️", "defense": 10, "price": 80}
}

DUNGEONS = {
    "forest": {"name": "Лесной монастырь", "emoji": "🌲", "difficulty": 1, "enemies": 3},
    "cave": {"name": "Пещера", "emoji": "⛰️", "difficulty": 2, "enemies": 5},
    "castle": {"name": "Замок", "emoji": "🏰", "difficulty": 3, "enemies": 7},
    "hell": {"name": "Адская пропасть", "emoji": "🔥", "difficulty": 4, "enemies": 10}
}

# ===================== FLASK APP =====================

app = Flask(__name__, template_folder='templates')

def init_db():
    """Инициализация БД"""
    conn = sqlite3.connect('runequestrpg.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            class TEXT,
            level INTEGER DEFAULT 1,
            experience INTEGER DEFAULT 0,
            health INTEGER,
            mana INTEGER,
            attack INTEGER,
            defense INTEGER,
            gold INTEGER,
            inventory TEXT DEFAULT '{}',
            total_kills INTEGER DEFAULT 0,
            total_damage INTEGER DEFAULT 0,
            playtime_seconds INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ===================== API ENDPOINTS =====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/classes')
def get_classes():
    return jsonify(CLASSES)

@app.route('/api/items')
def get_items():
    return jsonify(ITEMS)

@app.route('/api/dungeons')
def get_dungeons():
    return jsonify(DUNGEONS)

@app.route('/api/player')
def get_player():
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    
    conn = sqlite3.connect('runequestrpg.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM players WHERE user_id = ?', (user_id,))
    player = cursor.fetchone()
    conn.close()
    
    if not player:
        return jsonify({"error": "Player not found"}), 404
    
    player_dict = dict(player)
    player_dict['inventory'] = json.loads(player_dict['inventory'])
    return jsonify(player_dict)

@app.route('/api/create', methods=['POST'])
def create_player():
    data = request.json
    user_id = data.get('user_id')
    class_name = data.get('class')
    
    if not user_id or not class_name or class_name not in CLASSES:
        return jsonify({"error": "Invalid data"}), 400
    
    class_data = CLASSES[class_name]
    
    conn = sqlite3.connect('runequestrpg.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO players (user_id, class, health, mana, attack, defense, gold, inventory, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            class_name,
            class_data['health'],
            class_data['mana'],
            class_data['attack'],
            class_data['defense'],
            class_data['starting_gold'],
            json.dumps({}),
            datetime.now().isoformat()
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Player already exists"}), 409
    
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/enemies')
def get_enemies():
    return jsonify(ENEMIES)

@app.route('/api/leaderboard')
def get_leaderboard():
    conn = sqlite3.connect('runequestrpg.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, class, level, experience, gold, total_kills FROM players 
        ORDER BY level DESC, experience DESC LIMIT 10
    ''')
    
    leaders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(leaders)

@app.route('/api/update-stats', methods=['POST'])
def update_stats():
    data = request.json
    user_id = data.get('user_id')
    health = data.get('health')
    gold = data.get('gold')
    experience = data.get('experience')
    kills = data.get('kills', 0)
    damage = data.get('damage', 0)
    
    if not user_id:
        return jsonify({"error": "user_id required"}), 400
    
    conn = sqlite3.connect('runequestrpg.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE players 
        SET health = ?, gold = gold + ?, experience = experience + ?, 
            total_kills = total_kills + ?, total_damage = total_damage + ?
        WHERE user_id = ?
    ''', (health, gold, experience, kills, damage, user_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({"status": "success"})

# ===================== TELEGRAM BOT =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 ОТКРЫТЬ ИГРУ", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    await update.message.reply_text(
        f"👋 Добро пожаловать, {username}!\n\n"
        f"🎮 **RuneQuestRPG** - эпическая RPG игра в Telegram!\n\n"
        f"⚔️ Выбери класс, сражайся с врагами, собирай предметы и поднимайся в рейтинге!\n\n"
        f"✨ Особенности:\n"
        f"• 5 уникальных классов\n"
        f"• 8 типов врагов\n"
        f"• Система подземелий\n"
        f"• Магазин предметов\n"
        f"• Красивые анимации\n"
        f"• Рейтинг игроков",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 ОТКРЫТЬ ИГРУ", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("🏆 Рейтинг", callback_data="leaderboard")]
    ])
    
    await update.message.reply_text(
        "🎮 **Меню игры:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Статистика откроется в игре!", show_alert=False)

async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Рейтинг откроется в игре!", show_alert=False)

def setup_telegram_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CallbackQueryHandler(stats_callback, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^leaderboard$"))
    
    logger.info("✅ Telegram бот запущен")
    return application

# ===================== MAIN =====================

def main():
    logger.info(f"🌐 Flask сервер запущен на 0.0.0.0:{PORT}")
    logger.info(f"📱 Web App URL: {WEBAPP_URL}")
    app.run(host='0.0.0.0', port=PORT, debug=False)

if __name__ == '__main__':
    main()
