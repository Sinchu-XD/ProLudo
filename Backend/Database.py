from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL
import logging

logger = logging.getLogger("ludo_pro_db")

# ==========================================
# MONGO CLIENT (PRODUCTION SAFE SETTINGS)
# ==========================================

client = AsyncIOMotorClient(
    MONGO_URL,
    maxPoolSize=50,
    minPoolSize=5,
    serverSelectionTimeoutMS=5000,
    socketTimeoutMS=20000,
)

db = client.ludo_pro

users_collection = db.users
rooms_collection = db.rooms
games_collection = db.games
match_history_collection = db.match_history


# ==========================================
# CONNECTION TEST
# ==========================================

async def test_connection():
    try:
        await client.admin.command("ping")
        logger.info("✅ MongoDB Connected Successfully")
    except Exception as e:
        logger.error(f"❌ MongoDB Connection Failed: {e}")
        raise


# ==========================================
# INDEX CREATION
# ==========================================

async def create_indexes():
    await users_collection.create_index("user_id", unique=True)
    await rooms_collection.create_index("room_id", unique=True)
    await games_collection.create_index("game_id", unique=True)
    await match_history_collection.create_index("winner_id")

    logger.info("✅ MongoDB Indexes Created")


# ==========================================
# CLOSE CONNECTION (OPTIONAL)
# ==========================================

async def close_connection():
    client.close()
    logger.info("🛑 MongoDB Connection Closed")
