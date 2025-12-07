# 🎮 RuneQuestRPG Web App - КРАТКИЙ СТАРТ

## ⚡ САМОЕ ГЛАВНОЕ - 5 ШАГОВ

### 1. Получи Bot Token
```
→ Telegram: @BotFather
→ Команда: /newbot
→ Выбери имя, юзернейм
→ Получи токен (сохрани его!)
```

### 2. Создай папки и файлы
```bash
mkdir templates static logs
# Положи index.html в папку templates/
cp .env.example .env
```

### 3. Настрой .env
```
BOT_TOKEN=твой_токен_от_BotFather
WEBAPP_URL=http://localhost:5000  # пока локально
PORT=5000
```

### 4. Установи зависимости и запусти
```bash
pip install -r requirements.txt
python webapp_bot.py
```

### 5. Откройся в браузере
```
http://localhost:5000
```

---

## 🚀 ДЕПЛОЙ НА RENDER.COM (БЕСПЛАТНО)

### Шаг 1: GitHub
```bash
git init
git add .
git commit -m "Init"
git push origin main
```

### Шаг 2: Render Dashboard
1. render.com → Sign Up
2. GitHub Sign In
3. "New +" → "Web Service"
4. Выбери репо
5. Build Command: `pip install -r requirements.txt`
6. Start Command: `gunicorn webapp_bot:app`

### Шаг 3: Environment Variables
- BOT_TOKEN = твой токен
- WEBAPP_URL = твой URL на Render
- PORT = 5000

### Шаг 4: Deploy!
Нажми "Create Web Service" → жди 5 минут

---

## 📱 ВКЛЮЧЕНИЕ В TELEGRAM БОТЕ

### Вариант 1: BotFather (ЛЕГКИЙ)
```
1. @BotFather → /mybots → выбери бота
2. Bot Settings → Menu button
3. Edit menu button URL
4. Введи URL: https://твой-render-url.onrender.com
5. Done!
```

---

## 💡 СОВЕТЫ

1. **Для тестирования** используй локально (http://localhost:5000)
2. **Кнопка меню** появляется если нажать /start в боте
3. **URL для Web App** должен быть HTTPS на продакшене
4. **БД хранит все данные** - не удаляй `runequestrpg.db` на боевом сервере
5. **Логи смотри** в папке `logs/runequestrpg.log`

---

## 📞 ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ

1. Посмотри логи: `tail logs/runequestrpg.log`
2. Проверь консоль браузера: F12 → Console → Network
3. Проверь .env файл - все ли поля заполнены?
4. Перезагрузи страницу (Ctrl+Shift+R)
5. Перезапусти бота (Ctrl+C, потом python webapp_bot.py)

---

**Удачи с разработкой!** 🚀
