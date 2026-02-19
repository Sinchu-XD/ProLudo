import random
from datetime import datetime, timedelta
from Database import games_collection, users_collection, match_history_collection
from Config import TURN_TIME
from Lock_Manager import get_game_lock

SAFE_TILES = [0, 8, 13, 21, 26, 34, 39, 47]
TOTAL_PATH = 52


class GameEngine:

    # ====================================================
    # ROLL DICE
    # ====================================================
    @staticmethod
    async def roll_dice(game, user_id):

        lock = get_game_lock(game["game_id"])

        async with lock:

            game = await games_collection.find_one({"game_id": game["game_id"]})

            if not game or game["status"] != "playing":
                return {"error": "Game not active"}

            if game["current_turn"] != user_id:
                return {"error": "Not your turn"}

            if game.get("dice_value") is not None:
                return {"error": "Dice already rolled"}

            dice = random.randint(1, 6)

            await games_collection.update_one(
                {"game_id": game["game_id"]},
                {"$set": {
                    "dice_value": dice,
                    "turn_deadline": datetime.utcnow() + timedelta(seconds=TURN_TIME)
                }}
            )

            return {"dice": dice}

    # ====================================================
    # MOVE TOKEN
    # ====================================================
    @staticmethod
    async def move_token(game, user_id, token_index):

        lock = get_game_lock(game["game_id"])

        async with lock:

            game = await games_collection.find_one({"game_id": game["game_id"]})

            if not game or game["status"] != "playing":
                return {"error": "Game not active"}

            if game["current_turn"] != user_id:
                return {"error": "Not your turn"}

            if not isinstance(token_index, int) or token_index < 0 or token_index > 3:
                return {"error": "Invalid token"}

            dice = game.get("dice_value")
            if dice is None:
                return {"error": "Roll dice first"}

            player = next((p for p in game["players"] if p["user_id"] == user_id), None)
            if not player:
                return {"error": "Player not found"}

            token_pos = player["tokens"][token_index]

            # Cannot move already finished token
            if token_pos == TOTAL_PATH:
                return {"error": "Token already finished"}

            # 6 required to open
            if token_pos == -1:
                if dice != 6:
                    return {"error": "Need 6 to open"}
                new_pos = 0
            else:
                new_pos = token_pos + dice
                if new_pos > TOTAL_PATH:
                    return {"error": "Invalid move"}

            capture_happened = False

            # CAPTURE CHECK
            for opponent in game["players"]:
                if opponent["user_id"] == user_id:
                    continue

                for idx, opp_pos in enumerate(opponent["tokens"]):
                    if opp_pos == new_pos and new_pos not in SAFE_TILES:
                        opponent["tokens"][idx] = -1
                        capture_happened = True

            player["tokens"][token_index] = new_pos

            # WIN CHECK
            if new_pos == TOTAL_PATH:
                player["finished"] += 1

            winner = None
            if player["finished"] >= 4:
                winner = user_id

            bonus_turn = dice == 6 or capture_happened

            if not bonus_turn:
                current_index = game["players"].index(player)
                next_index = (current_index + 1) % len(game["players"])
                next_player = game["players"][next_index]["user_id"]
            else:
                next_player = user_id

            await games_collection.update_one(
                {"game_id": game["game_id"]},
                {"$set": {
                    "players": game["players"],
                    "current_turn": next_player,
                    "dice_value": None,
                    "turn_deadline": datetime.utcnow() + timedelta(seconds=TURN_TIME)
                }}
            )

            if winner:
                await GameEngine.finish_game(game["game_id"], winner)

            return {
                "new_position": new_pos,
                "capture": capture_happened,
                "bonus_turn": bonus_turn,
                "winner": winner
            }

    # ====================================================
    # FINISH GAME
    # ====================================================
    @staticmethod
    async def finish_game(game_id, winner_id):

        game = await games_collection.find_one({"game_id": game_id})

        if not game:
            return

        for player in game["players"]:

            user = await users_collection.find_one({"user_id": player["user_id"]})
            if not user:
                continue

            if player["user_id"] == winner_id:
                coins = user["coins"] + 50
                wins = user["wins"] + 1
                streak = user["win_streak"] + 1
                losses = user["losses"]
                result = "win"
            else:
                coins = user["coins"] + 5
                wins = user["wins"]
                losses = user["losses"] + 1
                streak = 0
                result = "loss"

            await users_collection.update_one(
                {"user_id": player["user_id"]},
                {"$set": {
                    "coins": coins,
                    "wins": wins,
                    "losses": losses,
                    "win_streak": streak
                }}
            )

        # Save match history
        await match_history_collection.insert_one({
            "match_id": game_id,
            "mode": game["mode"],
            "players": [
                {
                    "user_id": p["user_id"],
                    "result": "win" if p["user_id"] == winner_id else "loss"
                }
                for p in game["players"]
            ],
            "winner_id": winner_id,
            "created_at": datetime.utcnow()
        })

        await games_collection.update_one(
            {"game_id": game_id},
            {"$set": {"status": "finished"}}
        )
        
