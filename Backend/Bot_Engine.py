import asyncio
from Database import games_collection
from Game_Engine import GameEngine
from Lock_Manager import get_game_lock
from Connection_Manager import broadcast_to_game


class BotEngine:

    @staticmethod
    async def play_turn(game_id, bot_user_id):

        lock = get_game_lock(game_id)

        async with lock:

            game = await games_collection.find_one({"game_id": game_id})

            if not game or game["status"] != "playing":
                return

            if game["current_turn"] != bot_user_id:
                return

            player = next(
                (p for p in game["players"]
                 if p["user_id"] == bot_user_id and p["status"] == "bot"),
                None
            )

            if not player:
                return

            # Human-like thinking delay
            await asyncio.sleep(1.5)

            # ================= ROLL DICE =================
            dice_result = await GameEngine.roll_dice(game, bot_user_id)

            if "error" in dice_result:
                return

            dice = dice_result["dice"]

            game = await games_collection.find_one({"game_id": game_id})

            await broadcast_to_game(game, {
                "type": "dice_rolled",
                "player": bot_user_id,
                "dice": dice
            })

            await asyncio.sleep(1)

            # ================= SELECT TOKEN =================
            best_token = BotEngine.choose_best_token(game, player, dice)

            if best_token is None:
                # No valid move → skip handled by engine
                return

            move_result = await GameEngine.move_token(
                game,
                bot_user_id,
                best_token
            )

            if "error" in move_result:
                return

            game = await games_collection.find_one({"game_id": game_id})

            await broadcast_to_game(game, {
                "type": "token_moved",
                "player": bot_user_id,
                "position": move_result["new_position"],
                "capture": move_result["capture"],
                "bonus": move_result["bonus_turn"],
                "next_turn": game["current_turn"],
                "winner": move_result["winner"]
            })

            # ================= BONUS TURN LOOP =================
            if move_result["bonus_turn"] and not move_result["winner"]:
                await asyncio.sleep(1)
                await BotEngine.play_turn(game_id, bot_user_id)

    # ======================================================
    # SMART TOKEN SELECTION
    # ======================================================
    @staticmethod
    def choose_best_token(game, player, dice):

        valid_moves = []

        for idx, pos in enumerate(player["tokens"]):

            # Token finished
            if pos == 52:
                continue

            # Closed token
            if pos == -1:
                if dice == 6:
                    valid_moves.append((idx, 0))
                continue

            new_pos = pos + dice

            if new_pos > 52:
                continue

            valid_moves.append((idx, new_pos))

        if not valid_moves:
            return None

        # PRIORITY 1: Capture
        for idx, new_pos in valid_moves:
            for opponent in game["players"]:
                if opponent["user_id"] == player["user_id"]:
                    continue
                if new_pos in opponent["tokens"]:
                    return idx

        # PRIORITY 2: Highest progress
        best = max(valid_moves, key=lambda x: x[1])
        return best[0]
        
