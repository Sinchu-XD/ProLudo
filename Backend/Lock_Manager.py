import asyncio

game_locks = {}

def get_game_lock(game_id):
    if game_id not in game_locks:
        game_locks[game_id] = asyncio.Lock()
    return game_locks[game_id]
  
