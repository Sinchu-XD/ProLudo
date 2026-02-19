active_connections = {}


async def send_to_user(user_id, data):
    ws = active_connections.get(user_id)
    if ws:
        try:
            await ws.send_json(data)
        except:
            active_connections.pop(user_id, None)


async def broadcast_to_game(game, data):
    for player in game.get("players", []):
        await send_to_user(player["user_id"], data)

    for spectator in game.get("spectators", []):
        await send_to_user(spectator, data)
      
