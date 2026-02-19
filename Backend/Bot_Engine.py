import asyncio
import random
from database import games_collection
from game_engine import GameEngine


class BotEngine:

    @staticmethod
    async def play_turn(game_id, bot_user_id):

        # Delay for human-like thinking
        await asyncio.sleep(1.5)

        game = await games_collection.find_one({"game_id": game_id})

        if not game or game["status"] != "playing":
            return

        if game["current_turn"] != bot_user_id:
            return

        # Roll dice
        dice_result = await GameEngine.roll_dice(game, bot_user_id)

        if "error" in dice_result:
            return

        dice = dice_result["dice"]

        game = await games_collection.find_one({"game_id": game_id})

        player = next(p for p in game["players"] if p["user_id"] == bot_user_id)

        best_token = BotEngine.choose_best_token(game, player, dice)

        if best_token is None:
            return  # no move possible

        await asyncio.sleep(1)

        await GameEngine.move_token(game, bot_user_id, best_token)

    # ======================================================
    # SMART TOKEN SELECTION
    # ======================================================
    @staticmethod
    def choose_best_token(game, player, dice):

        valid_moves = []

        for idx, pos in enumerate(player["tokens"]):

            # Token closed
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

        # PRIORITY 2: Furthest progress
        best = max(valid_moves, key=lambda x: x[1])
        return best[0]
      
