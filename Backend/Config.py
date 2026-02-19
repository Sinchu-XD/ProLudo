import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# ENVIRONMENT MODE
# ==========================================

ENV = os.getenv("ENV", "development").lower()
DEBUG = ENV != "production"

# ==========================================
# REQUIRED VARIABLES
# ==========================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8231818663:AAFtLagnRx0OSfIBO_a0RcXWkgRIExJsOqQ")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is not set in environment variables")

# ==========================================
# DATABASE
# ==========================================

MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://Vexera:Vexera@vexera.wtrsmyc.mongodb.net/?appName=Vexera")

# ==========================================
# GAME SETTINGS (TYPE SAFE)
# ==========================================

TURN_TIME = int(os.getenv("TURN_TIME", 30))          # seconds
RECONNECT_TIME = int(os.getenv("RECONNECT_TIME", 60))  # seconds
MAX_SPECTATORS = int(os.getenv("MAX_SPECTATORS", 20))

# ==========================================
# SECURITY SETTINGS
# ==========================================

MAX_AUTH_AGE = int(os.getenv("MAX_AUTH_AGE", 86400))  # 24 hours

# ==========================================
# SERVER SETTINGS
# ==========================================

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# ==========================================
# PRINT MODE (OPTIONAL DEBUG)
# ==========================================

if DEBUG:
    print("⚙ Running in DEVELOPMENT mode")
else:
    print("🚀 Running in PRODUCTION mode")
