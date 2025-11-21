import os

BOT_TOKEN = os.getenv("BOT_TOKEN") or "PASTE_YOUR_TOKEN_HERE"  # токен бота от BotFather или из переменной окружения

DATA_FILE = "data.json"

XP_PER_MESSAGE = 1
XP_COOLDOWN_SECONDS = 0

DEFAULT_RANKS = [
    {"xp_min": 0, "name": "F"},
    {"xp_min": 100, "name": "D"},
    {"xp_min": 200, "name": "C"},
    {"xp_min": 300, "name": "B"},
    {"xp_min": 400, "name": "A"},
    {"xp_min": 500, "name": "S"},
    {"xp_min": 600, "name": "S+"},
    {"xp_min": 700, "name": "S++"},
]
