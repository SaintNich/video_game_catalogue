import datetime as dt
import os
import requests
from access_token import create_header
from config import STEAM_ENDPOINT, IGDB_GAMES_ENDPOINT, get_conn
from dotenv import load_dotenv
from igdb import igdb_search, user_selection_to_query, game_processing

load_dotenv()
API_KEY = os.getenv('api_key')
STEAM_ID = os.getenv('steam_id')

def get_steam_info() -> list:
  steam_url = STEAM_ENDPOINT + '?key=' + API_KEY + '&steamid=' + STEAM_ID + '&include_appinfo=true&format=json'
  steam_response = requests.get(steam_url).json()
  steam_games = steam_response.get('response').get('games')

  return steam_games

def steam_selection_to_query(steam_game_name: str, steam_game: dict) -> int:
  body = f"fields name, first_release_date; search \"{steam_game_name}\"; limit 50;"
  steam_search_results = requests.post(IGDB_GAMES_ENDPOINT, headers = create_header(), data = body).json()

  print(f"Game to select: {steam_game_name}")
  for i, result in enumerate(steam_search_results):
    game_title = result.get('name')
    release_year = dt.datetime.fromtimestamp(result.get('first_release_date')).year if result.get('first_release_date') else 'unknown'
    igdb_id = result.get('id')
    print(f"{i+1}. {game_title}, released in {release_year} [ID = {igdb_id}]")

  try:
    if steam_search_results:
      while True:
        steam_selection = input("Choose the correct game: ")
        if 1 <= int(steam_selection) <= len(steam_search_results):
          break
        print("Be sure to choose a number in the list. ")
      
      choice = steam_search_results[int(steam_selection) - 1]
      igdb_id = choice.get('id')
      
      return igdb_id
    
    else:
      print(f"No results for {steam_game_name}")
  
  except ValueError:
    print("Please enter an integer. ")
    return steam_selection_to_query(steam_game)
  
def check_if_steam_game_exists(steam_game_id: int) -> bool:
  conn = get_conn()

  is_steam_id_in_games = conn.execute("""
    SELECT steam_id FROM games
    WHERE steam_id = ?
  """, (steam_game_id,)).fetchone()
  
  steam_id_in_games = is_steam_id_in_games[0] if is_steam_id_in_games else 0

  if steam_id_in_games == steam_game_id:
    return True
  else:
    return False

def write_additional_steam_game_information (steam_game_id: int, igdb_id: int):
  conn = get_conn()

  conn.execute("""
    UPDATE games SET steam_id = ?
    WHERE igdb_id = ?
  """, (
    steam_game_id,
    igdb_id
  ))

  conn.commit()
  conn.close()

def main():
  steam_games = get_steam_info()

  for steam_game in steam_games:
    steam_game_name = steam_game.get('name')
    steam_game_id = steam_game.get('appid')
    steam_game_playtime = round((steam_game.get('playtime_forever') / 60), 2) # currently a placeholder for future use
    igdb_id = steam_selection_to_query(steam_game_name, steam_game)
    
    if check_if_steam_game_exists(steam_game_id):
      continue
    else:
      if igdb_id is None:
        search_results = igdb_search()
        igdb_id = user_selection_to_query(search_results)

      game_processing(igdb_id)  
      write_additional_steam_game_information(steam_game_id, igdb_id)

if __name__ == '__main__':
  main()