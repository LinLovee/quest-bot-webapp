# -*- coding: utf-8 -*-
"""
RuneQuestRPG Web App — Telegram Bot с Web App версией
Модифицированно из v5.3 под Flask + HTML5 Web App
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
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app.com")
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
        "health": 120,
        "mana": 30,
        "attack": 15,
        "defense": 8,
        "crit_chance": 5,
        "starting_gold": 100,
        "spell_power": 0,
        "dodge_chance": 3,
        "element": Element.PHYSICAL.value,
    },
    "mage": {
        "name": "Маг",
        "emoji": "🪄",
        "description": "Слабое тело, но мощная магия.",
        "health": 70,
        "mana": 130,
        "attack": 8,
        "defense": 3,
        "crit_chance": 8,
        "starting_gold": 150,
        "spell_power": 25,
        "dodge_chance": 2,
        "element": Element.ARCANE.value,
    },
    "rogue": {
        "name": "Разбойник",
        "emoji": "🗡️",
        "description": "Криты и уклонения.",
        "health": 85,
        "mana": 50,
        "attack": 19,
        "defense": 5,
        "crit_chance": 22,
        "starting_gold": 130,
        "spell_power": 5,
        "dodge_chance": 12,
        "element": Element.SHADOW.value,
    },
    "paladin": {
        "name": "Паладин",
        "emoji": "✨",
        "description": "Танк со священной силой.",
        "health": 140,
        "mana": 80,
        "attack": 13,
        "defense": 15,
        "crit_chance": 4,
        "starting_gold": 140,
        "spell_power": 12,
        "dodge_chance": 4,
        "element": Element.HOLY.value,
    },
}

ENEMIES = {
    "goblin": {"name": "Гоблин", "emoji": "👹", "hp": 20, "damage": 8},
    "orc": {"name": "Орк", "emoji": "👿", "hp": 35, "damage": 12},
    "skeleton": {"name": "Скелет", "emoji": "☠️", "hp": 25, "damage": 10},
    "troll": {"name": "Тролль", "emoji": "🧌", "hp": 45, "damage": 15},
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
    
    return jsonify(dict(player))

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
            INSERT INTO players (user_id, class, health, mana, attack, defense, gold, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            class_name,
            class_data['health'],
            class_data['mana'],
            class_data['attack'],
            class_data['defense'],
            class_data['starting_gold'],
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

# ===================== TELEGRAM BOT =====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 ОТКРЫТЬ ИГРУ", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    await update.message.reply_text(
        f"👋 Добро пожаловать, {username}! Добро пожаловать в RuneQuestRPG Web App!",
        reply_markup=keyboard
    )

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 ОТКРЫТЬ ИГРУ", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📖 Справка", callback_data="help")]
    ])
    
    await update.message.reply_text(
        "🎯 Главное меню:",
        reply_markup=keyboard
    )

def setup_telegram_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("menu", menu_command))
    
    logger.info("✅ Telegram бот запущен")
    return application

# ===================== MAIN =====================

def main():
    logger.info(f"🌐 Flask сервер запущен на 0.0.0.0:{PORT}")
    logger.info(f"📱 Web App URL: {WEBAPP_URL}")
    app.run(host='0.0.0.0', port=PORT, debug=False)

if __name__ == '__main__':
    main()
