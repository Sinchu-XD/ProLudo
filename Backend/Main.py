from fastapi import FastAPI, WebSocket
from WebSocket_Handler import handle_websocket

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_websocket(websocket)
  
import asyncio
from Timer_Worker import TimerWorker

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(TimerWorker.start())
    
