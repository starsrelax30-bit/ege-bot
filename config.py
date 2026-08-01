import os

BOT_TOKEN = os.environ.get('BOT_TOKEN', '')
WEBAPP_URL = os.environ.get('WEBAPP_URL', '')
OWNER_ID = int(os.environ.get('OWNER_ID', '0'))

CATEGORIES = {
    "all": "Все слова",
    "nouns": "Существительные",
    "adjectives": "Прилагательные",
    "verbs": "Глаголы",
    "participles": "Причастия",
    "gerunds": "Деепричастия",
    "adverbs": "Наречия"
}

WORDS_BY_CATEGORY = {
    "nouns": ["аэропОрты", "бАнты", "бОроду", "бухгАлтеров"],
    "adjectives": ["вернА", "знАчимый", "красИвее"],
    "verbs": ["бралА", "бралАсь", "взялА"],
    "participles": ["довезЁнный", "зАгнутый", "зАнятый"],
    "gerunds": ["закУпорив", "начАв", "начАвшись"],
    "adverbs": ["вОвремя", "дОверху", "донЕльзя"]
}

DB_NAME = "ege_bot.db"
