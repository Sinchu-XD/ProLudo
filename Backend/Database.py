from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

client = AsyncIOMotorClient(MONGO_URL)
db = client.ludo_pro

users_collection = db.users
rooms_collection = db.rooms
games_collection = db.games
match_history_collection = db.match_history

