def create_user_model(user):
    return {
        "user_id": user["id"],
        "telegram_name": user.get("first_name"),
        "username": user.get("username"),
        "avatar_url": user.get("photo_url"),
        "coins": 100,
        "wins": 0,
        "losses": 0,
        "win_streak": 0,
        "last_daily_claim": None,
    }

def create_room_model(room_id, host_id, mode, room_type):
    return {
        "room_id": room_id,
        "host_id": host_id,
        "mode": mode,
        "type": room_type,
        "players": [host_id],
        "spectators": [],
        "max_players": 2 if mode == "2p" else 4,
        "status": "waiting",
    }
  
