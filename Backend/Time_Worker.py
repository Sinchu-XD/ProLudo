import asyncio
from datetime import datetime, timedelta
from database import games_collection
from config import TURN_TIME, RECONNECT_TIME
from bot_engine import BotEngine


class TimerWorker:

    @staticmethod
    async def start():
        while True:
            await TimerWorker.check_games()
            await asyncio.sleep(1)

    # ==============================================
    # CHECK ALL ACTIVE GAMES
    # ==============================================
    @staticmethod
    async def check_games():
        now = datetime.utcnow()

        active_games = games_collection.find({"status": "playing"})

        async for game in active_games:

            # ------------------------------
            # TURN TIMEOUT CHECK
            # ------------------------------
            deadline = game.get("turn_deadline")

            if deadline and now > deadline:
                await TimerWorker.skip_turn(game)

            # ------------------------------
            # DISCONNECT CHECK
            # ------------------------------
            for player in game["players"]:
                if player.get("status") == "disconnected":
                    disconnect_time = player.get("disconnect_time")

                    if disconnect_time and now > disconnect_time + timedelta(seconds=RECONNECT_TIME):
                        await TimerWorker.replace_with_bot(game, player["user_id"])

    # ==============================================
    # SKIP TURN
    # ==============================================
    @staticmethod
    async def skip_turn(game):

        current_turn = game["current_turn"]

        players = game["players"]
        current_index = next(
            i for i, p in enumerate(players)
            if p["user_id"] == current_turn
        )

        next_index = (current_index + 1) % len(players)
        next_player = players[next_index]["user_id"]

        await games_collection.update_one(
            {"game_id": game["game_id"]},
            {"$set": {
                "current_turn": next_player,
                "dice_value": None,
                "turn_deadline": datetime.utcnow() + timedelta(seconds=TURN_TIME)
            }}
        )

    # ==============================================
    # DISCONNECT MARK
    # ==============================================
    @staticmethod
    async def mark_disconnected(game_id, user_id):

        await games_collection.update_one(
            {"game_id": game_id, "players.user_id": user_id},
            {"$set": {
                "players.$.status": "disconnected",
                "players.$.disconnect_time": datetime.utcnow()
            }}
        )

    # ==============================================
    # RECONNECT MARK
    # ==============================================
    @staticmethod
    async def mark_reconnected(game_id, user_id):

        await games_collection.update_one(
            {"game_id": game_id, "players.user_id": user_id},
            {"$set": {
                "players.$.status": "active",
                "players.$.disconnect_time": None
            }}
        )

    # ==============================================
    # BOT REPLACEMENT
    # ==============================================
    @staticmethod
    async def replace_with_bot(game, user_id):

        await games_collection.update_one(
            {"game_id": game["game_id"], "players.user_id": user_id},
            {"$set": {
                "players.$.status": "bot"
            }}
        )

        # Let bot immediately act if it's bot's turn
        if game["current_turn"] == user_id:
            await BotEngine.play_turn(game["game_id"], user_id)
      
