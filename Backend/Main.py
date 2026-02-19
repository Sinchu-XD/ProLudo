import asyncio
import logging
from fastapi import FastAPI, WebSocket
from contextlib import asynccontextmanager

from WebSocket_Handler import handle_websocket
from Timer_Worker import TimerWorker
from Database import (
    test_connection,
    create_indexes,
    close_connection
)

# ==========================================
# LOGGING CONFIG
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("ludo_pro_backend")

# ==========================================
# LIFESPAN (Recommended for FastAPI)
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Ludo Pro Backend Starting...")

    # Mongo connection test
    await test_connection()

    # Create indexes
    await create_indexes()

    # Start Timer Worker
    timer_task = asyncio.create_task(TimerWorker.start())
    logger.info("⏳ Timer Worker Started")

    yield

    # Shutdown section
    logger.info("🛑 Ludo Pro Backend Shutting Down...")

    timer_task.cancel()
    try:
        await timer_task
    except asyncio.CancelledError:
        logger.info("✅ Timer Worker Stopped")

    await close_connection()
    logger.info("✅ Mongo Connection Closed")


# ==========================================
# FASTAPI APP
# ==========================================

app = FastAPI(
    title="Ludo Pro Backend",
    version="1.0.0",
    lifespan=lifespan
)

# ==========================================
# WEBSOCKET ROUTE
# ==========================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_websocket(websocket)


# ==========================================
# HEALTH CHECK (FOR NGINX / MONITORING)
# ==========================================

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Ludo Pro Backend"}
    
