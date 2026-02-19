from fastapi import WebSocket
from database import users_collection, rooms_collection
from models import create_user_model, create_room_model
from auth import verify_telegram_init_data
import uuid
import json

active_connections = {}  # user_id -> websocket


async def send_to_user(user_id, data):
    ws = active_connections.get(user_id)
    if ws:
        await ws.send_json(data)


async def broadcast_to_room(room, data):
    for user_id in room["players"]:
        await send_to_user(user_id, data)

    for spectator_id in room.get("spectators", []):
        await send_to_user(spectator_id, data)

