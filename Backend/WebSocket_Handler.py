from fastapi import WebSocket
from Database import users_collection, rooms_collection, games_collection
from Models import create_user_model, create_room_model
from Auth import verify_telegram_init_data
from Game_Engine import GameEngine
from Timer_Worker import TimerWorker
import uuid
import json
from datetime import datetime

# ===============================
# CONNECTION MANAGER
# ===============================



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

            # ================= AUTH =================
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

            # ================= CREATE ROOM =================
            elif action == "create_room":
                mode = data.get("mode")
                room_type = data.get("type")

                room_id = str(uuid.uuid4())
                room = create_room_model(room_id, user_id, mode, room_type)

                if room_type == "private":
                    room["room_code"] = str(uuid.uuid4())[:6].upper()

                await rooms_collection.insert_one(room)

                await websocket.send_json({
                    "type": "room_created",
                    "room": room
                })

            # ================= JOIN ROOM =================
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

                for uid in room["players"]:
                    await send_to_user(uid, {
                        "type": "player_joined",
                        "players": room["players"]
                    })

            # ================= START GAME =================
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

                colors = ["red", "blue", "green", "yellow"]
                players_data = []

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
                    "spectators": [],
                    "current_turn": players_data[0]["user_id"],
                    "dice_value": None,
                    "turn_deadline": datetime.utcnow(),
                    "status": "playing",
                    "created_at": datetime.utcnow()
                }

                await games_collection.insert_one(game_data)

                await rooms_collection.update_one(
                    {"room_id": room_id},
                    {"$set": {"status": "playing"}}
                )

                await broadcast_to_game(game_data, {
                    "type": "game_started",
                    "game": game_data
                })

            # ================= ROLL DICE =================
            elif action == "roll_dice":
                game_id = data.get("game_id")
                game = await games_collection.find_one({"game_id": game_id})

                if not game:
                    continue

                result = await GameEngine.roll_dice(game, user_id)

                if "error" in result:
                    await websocket.send_json(result)
                    continue

                game = await games_collection.find_one({"game_id": game_id})

                await broadcast_to_game(game, {
                    "type": "dice_rolled",
                    "player": user_id,
                    "dice": result["dice"]
                })

            # ================= MOVE TOKEN =================
            elif action == "move_token":
                game_id = data.get("game_id")
                token_index = data.get("token_index")

                game = await games_collection.find_one({"game_id": game_id})

                if not game:
                    continue

                result = await GameEngine.move_token(game, user_id, token_index)

                if "error" in result:
                    await websocket.send_json(result)
                    continue

                game = await games_collection.find_one({"game_id": game_id})

                await broadcast_to_game(game, {
                    "type": "token_moved",
                    "player": user_id,
                    "position": result["new_position"],
                    "capture": result["capture"],
                    "bonus": result["bonus_turn"],
                    "next_turn": game["current_turn"],
                    "winner": result["winner"]
                })

                if result["winner"]:
                    await broadcast_to_game(game, {
                        "type": "game_finished",
                        "winner": result["winner"]
                    })

            # ================= RECONNECT =================
            elif action == "reconnect":
                game_id = data.get("game_id")

                await TimerWorker.mark_reconnected(game_id, user_id)

                game = await games_collection.find_one({"game_id": game_id})

                await websocket.send_json({
                    "type": "game_state",
                    "game": game
                })

    except Exception:
        if user_id:
            active_connections.pop(user_id, None)

            # mark disconnected in active game
            game = await games_collection.find_one({
                "status": "playing",
                "players.user_id": user_id
            })

            if game:
                await TimerWorker.mark_disconnected(
                    game["game_id"],
                    user_id
                )

        await websocket.close()
                    
