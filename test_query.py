from igdb import header, IGDB_GAMES_ENDPOINT
import requests

gamepass_id = '9N255K81XBD3'

body = f"fields external_games.name, external_games.external_game_source, external_games.uid; search \"Final Fantasy VI\";"

search_results = requests.post(IGDB_GAMES_ENDPOINT, headers = header, data = body).json()

for search_result in search_results:
    if search_result.get('external_games'):
        for external_game in search_result.get('external_games'):
            if external_game.get('uid') == gamepass_id:
                print(search_result.get('id'), external_game)

#external_games.external_game_source, external_games.name, external_games.platform, external_games.uid