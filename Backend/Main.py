from fastapi import FastAPI, WebSocket
from websocket_handler import handle_websocket

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_websocket(websocket)
  
