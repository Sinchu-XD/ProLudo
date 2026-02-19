import asyncio
from datetime import datetime, timedelta
from Database import games_collection
from Config import TURN_TIME, RECONNECT_TIME
from Bot_Engine import BotEngine
from Lock_Manager import get_game_lock
from WebSocket_Handler import send_to_user


class TimerWorker:

    @staticmethod
    async def start():
        while True:
            await TimerWorker.check_games()
            await TimerWorker.cleanup_finished_games()
            await asyncio.sleep(1)

    # ==============================================
    # CHECK ALL ACTIVE GAMES
    # ==============================================
    @staticmethod
    async def check_games():
        now = datetime.utcnow()

        active_games = games_collection.find({"status": "playing"})

        async for game in active_games:

            lock = get_game_lock(game["game_id"])

            async with lock:

                # Reload fresh state
                game = await games_collection.find_one(
                    {"game_id": game["game_id"]}
                )

                if not game or game["status"] != "playing":
                    continue

                # ---------------- TURN TIMEOUT ----------------
                deadline = game.get("turn_deadline")

                if deadline and now > deadline:
                    await TimerWorker.skip_turn(game)

                # ---------------- DISCONNECT CHECK ----------------
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

        players = game["players"]
        current_turn = game["current_turn"]

        current_index = next(
            (i for i, p in enumerate(players)
             if p["user_id"] == current_turn),
            None
        )

        if current_index is None:
            return

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

        # Broadcast skip
        for p in players:
            await send_to_user(p["user_id"], {
                "type": "turn_skipped",
                "next_turn": next_player
            })

    # ==============================================
    # MARK DISCONNECTED
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
    # MARK RECONNECTED
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

        # Broadcast bot replacement
        for p in game["players"]:
            await send_to_user(p["user_id"], {
                "type": "player_replaced_by_bot",
                "player": user_id
            })

        # If bot turn, play immediately
        if game["current_turn"] == user_id:
            await BotEngine.play_turn(game["game_id"], user_id)

    # ==============================================
    # CLEANUP FINISHED GAMES
    # ==============================================
    @staticmethod
    async def cleanup_finished_games():

        threshold = datetime.utcnow() - timedelta(minutes=30)

        await games_collection.delete_many({
            "status": "finished",
            "created_at": {"$lt": threshold}
        })
        
