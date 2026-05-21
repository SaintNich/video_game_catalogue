import datetime as dt
import os
import requests
import sqlite3
from access_token import create_header
from config import STEAM_ENDPOINT, IGDB_GAMES_ENDPOINT, get_conn
from dotenv import load_dotenv
from igdb import game_processing

load_dotenv()
API_KEY = os.getenv('api_key')
STEAM_ID = os.getenv('steam_id')

def get_steam_info() -> list:
  steam_url = STEAM_ENDPOINT + '?key=' + API_KEY + '&steamid=' + STEAM_ID + '&include_appinfo=true&format=json'
  steam_response = requests.get(steam_url).json()
  steam_games = steam_response.get('response').get('games')

  return steam_games

def steam_selection_to_query(steam_game: dict) -> int:
  steam_game_name = steam_game.get('name')
  body = f"fields name, first_release_date; search \"{steam_game_name}\"; limit 20;"
  steam_search_results = requests.post(IGDB_GAMES_ENDPOINT, headers = create_header(), data = body).json()

  for i, result in enumerate(steam_search_results):
    game_title = result.get('name')
    release_year = dt.datetime.fromtimestamp(result.get('first_release_date')).year if result.get('first_release_date') else 'unknown'
    igdb_id = result.get('id')
    print(f"{i+1}. {game_title}, released in {release_year} [ID = {igdb_id}]")


def main():
  steam_games = get_steam_info()

  for steam_game in steam_games:
    steam_selection_to_query(steam_game)


if __name__ == '__main__':
  main()
