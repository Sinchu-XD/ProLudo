
from datetime import datetime
import uuid


# ==========================================
# USER MODEL
# ==========================================

def create_user_model(user: dict) -> dict:
    return {
        "user_id": user["id"],
        "telegram_name": user.get("first_name", ""),
        "username": user.get("username", ""),
        "avatar_url": user.get("photo_url", None),

        # Economy
        "coins": 100,
        "wins": 0,
        "losses": 0,
        "win_streak": 0,

        # Daily reward
        "last_daily_claim": None,

        # Metadata
        "created_at": datetime.utcnow(),
        "is_banned": False,
    }


# ==========================================
# ROOM MODEL
# ==========================================

def create_room_model(room_id: str, host_id: int, mode: str, room_type: str) -> dict:

    if mode not in ["2p", "4p"]:
        raise ValueError("Invalid game mode")

    if room_type not in ["public", "private"]:
        raise ValueError("Invalid room type")

    return {
        "room_id": room_id,
        "room_code": None,  # will be filled for private rooms
        "host_id": host_id,
        "mode": mode,
        "type": room_type,

        "players": [host_id],
        "spectators": [],

        "max_players": 2 if mode == "2p" else 4,

        "status": "waiting",  # waiting | playing | finished

        "created_at": datetime.utcnow(),
    }


# ==========================================
# GAME MODEL (Optional Helper)
# ==========================================

def create_game_model(room: dict) -> dict:

    colors = ["red", "blue", "green", "yellow"]

    players_data = []

    for idx, uid in enumerate(room["players"]):
        players_data.append({
            "user_id": uid,
            "color": colors[idx],
            "tokens": [-1, -1, -1, -1],
            "finished": 0,
            "status": "active",  # active | disconnected | bot
        })

    return {
        "game_id": room["room_id"],
        "mode": room["mode"],
        "players": players_data,
        "spectators": [],

        "current_turn": players_data[0]["user_id"],
        "dice_value": None,
        "turn_deadline": None,

        "status": "playing",
        "created_at": datetime.utcnow(),
    }
