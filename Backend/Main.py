import asyncio
import logging
from fastapi import FastAPI, WebSocket
from websocket_handler import handle_websocket
from timer_worker import TimerWorker
from database import (
    users_collection,
    rooms_collection,
    games_collection,
    match_history_collection
)

app = FastAPI()

# ==========================================
# LOGGING CONFIG
# ==========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ludo_pro_backend")


# ==========================================
# WEBSOCKET ROUTE
# ==========================================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_websocket(websocket)


# ==========================================
# STARTUP EVENT
# ==========================================
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Ludo Pro Backend Starting...")

    # Create Mongo Indexes (IMPORTANT)
    await users_collection.create_index("user_id", unique=True)
    await rooms_collection.create_index("room_id", unique=True)
    await games_collection.create_index("game_id", unique=True)
    await match_history_collection.create_index("winner_id")

    logger.info("✅ Mongo Indexes Ready")

    # Start Timer Worker
    asyncio.create_task(TimerWorker.start())

    logger.info("⏳ Timer Worker Started")


# ==========================================
# SHUTDOWN EVENT
# ==========================================
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Ludo Pro Backend Shutting Down...")
