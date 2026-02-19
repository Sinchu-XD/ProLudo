from fastapi import WebSocket
from database import users_collection, rooms_collection, games_collection
from models import create_user_model, create_room_model
from auth import verify_telegram_init_data
import uuid
import json
from datetime import datetime

# ===============================
# CONNECTION MANAGER
# ===============================

active_connections = {}  # user_id -> websocket


async def send_to_user(user_id, data):
    ws = active_connections.get(user_id)
    if ws:
        await ws.send_json(data)


async def broadcast_to_room(room, data):
    for uid in room.get("players", []):
        await send_to_user(uid, data)

    for sid in room.get("spectators", []):
        await send_to_user(sid, data)


# ===============================
# MAIN WEBSOCKET HANDLER
# ===============================

async def handle_websocket(websocket: WebSocket):
    await websocket.accept()

    user_id = None

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            # ======================================
            # AUTH
            # ======================================
            if action == "auth":
                init_data = data.get("init_data")

                if not verify_telegram_init_data(init_data):
                    await websocket.close()
                    return

                user = json.loads(data["user"])
                user_id = user["id"]

                active_connections[user_id] = websocket

                existing = await users_collection.find_one({"user_id": user_id})
                if not existing:
                    await users_collection.insert_one(create_user_model(user))

                await websocket.send_json({"type": "auth_success"})

            # ======================================
            # CREATE ROOM
            # ======================================
            elif action == "create_room":
                mode = data.get("mode")  # 2p / 4p
                room_type = data.get("type")  # public/private

                room_id = str(uuid.uuid4())
                room = create_room_model(room_id, user_id, mode, room_type)

                if room_type == "private":
                    room["room_code"] = str(uuid.uuid4())[:6].upper()

                await rooms_collection.insert_one(room)

                await websocket.send_json({
                    "type": "room_created",
                    "room": room
                })

            # ======================================
            # JOIN ROOM
            # ======================================
            elif action == "join_room":
                room_id = data.get("room_id")

                room = await rooms_collection.find_one({"room_id": room_id})

                if not room:
                    await websocket.send_json({"error": "Room not found"})
                    continue

                if len(room["players"]) >= room["max_players"]:
                    await websocket.send_json({"error": "Room full"})
                    continue

                if user_id in room["players"]:
                    continue

                await rooms_collection.update_one(
                    {"room_id": room_id},
                    {"$push": {"players": user_id}}
                )

                room = await rooms_collection.find_one({"room_id": room_id})

                await broadcast_to_room(room, {
                    "type": "player_joined",
                    "players": room["players"]
                })

            # ======================================
            # QUICK MATCH (PUBLIC MATCHMAKING)
            # ======================================
            elif action == "quick_match":
                mode = data.get("mode")

                room = await rooms_collection.find_one({
                    "mode": mode,
                    "type": "public",
                    "status": "waiting",
                    "$expr": {"$lt": [{"$size": "$players"}, "$max_players"]}
                })

                if room:
                    await rooms_collection.update_one(
                        {"room_id": room["room_id"]},
                        {"$push": {"players": user_id}}
                    )
                else:
                    room_id = str(uuid.uuid4())
                    room = create_room_model(room_id, user_id, mode, "public")
                    await rooms_collection.insert_one(room)

                room = await rooms_collection.find_one({"room_id": room["room_id"]})

                await broadcast_to_room(room, {
                    "type": "match_update",
                    "players": room["players"]
                })

            # ======================================
            # SPECTATOR JOIN
            # ======================================
            elif action == "watch_game":
                room_id = data.get("room_id")

                room = await rooms_collection.find_one({"room_id": room_id})

                if not room:
                    await websocket.send_json({"error": "Room not found"})
                    continue

                if room["type"] != "public":
                    await websocket.send_json({"error": "Private room"})
                    continue

                if len(room.get("spectators", [])) >= 20:
                    await websocket.send_json({"error": "Spectator limit reached"})
                    continue

                await rooms_collection.update_one(
                    {"room_id": room_id},
                    {"$push": {"spectators": user_id}}
                )

                room = await rooms_collection.find_one({"room_id": room_id})

                await websocket.send_json({
                    "type": "spectator_joined",
                    "room": room
                })

            # ======================================
            # HOST START GAME
            # ======================================
            elif action == "start_game":
                room_id = data.get("room_id")

                room = await rooms_collection.find_one({"room_id": room_id})

                if not room:
                    await websocket.send_json({"error": "Room not found"})
                    continue

                if room["host_id"] != user_id:
                    await websocket.send_json({"error": "Only host can start"})
                    continue

                if len(room["players"]) != room["max_players"]:
                    await websocket.send_json({"error": "Room not full"})
                    continue

                players_data = []
                colors = ["red", "blue", "green", "yellow"]

                for idx, uid in enumerate(room["players"]):
                    players_data.append({
                        "user_id": uid,
                        "color": colors[idx],
                        "tokens": [-1, -1, -1, -1],
                        "finished": 0,
                        "status": "active"
                    })

                game_data = {
                    "game_id": room_id,
                    "mode": room["mode"],
                    "players": players_data,
                    "current_turn": players_data[0]["user_id"],
                    "dice_value": None,
                    "turn_deadline": None,
                    "status": "playing",
                    "created_at": datetime.utcnow()
                }

                await games_collection.insert_one(game_data)

                await rooms_collection.update_one(
                    {"room_id": room_id},
                    {"$set": {"status": "playing"}}
                )

                await broadcast_to_room(room, {
                    "type": "game_started",
                    "game": game_data
                })

    except Exception:
        if user_id:
            active_connections.pop(user_id, None)

        await websocket.close()
