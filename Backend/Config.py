import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

TURN_TIME = 30
RECONNECT_TIME = 60
MAX_SPECTATORS = 20
