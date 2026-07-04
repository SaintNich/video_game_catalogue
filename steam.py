import json
import logging
import os
import sqlite3

import requests
from dotenv import load_dotenv

from config import STEAM_ENDPOINT, get_conn
from user_relationship import create_user_game_relationship

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

log = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("api_key")
STEAM_ID = os.getenv("steam_id")


def get_steam_info() -> list:
    try:
        steam_url = (
            STEAM_ENDPOINT
            + "?key="
            + API_KEY
            + "&steamid="
            + STEAM_ID
            + "&include_appinfo=true&format=json"
        )
        response = requests.get(steam_url)

        log.debug(
            f"Response Status Code: {response.status_code} | URL: {response.url} | Time: {response.elapsed.total_seconds()}s | Body Preview: {response.text[:200]}"
        )
        response.raise_for_status()

        steam_response = response.json()
        steam_games = (
            steam_response.get("response").get("games")
            if steam_response.get("response")
            else None
        )

    except requests.RequestException as e:
        log.error(f"Steam API request failed: {type(e).__name__}: {e}")
        return []

    except json.JSONDecodeError as e:
        log.error(f"JSON Decoding failed: {e}")
        return []

    except Exception as e:
        log.error(
            f"Unknow error occurred getting steam information: {type(e).__name__}: {e}"
        )
        return []

    else:
        if steam_games:
            log.info("Steam API query successful")
            return steam_games
        else:
            log.warning("Steam API query unsuccessful")
            return []


def check_if_steam_game_exists(steam_game_id: int) -> bool:
    conn = get_conn()
    try:
        is_steam_id_in_games = conn.execute(
            """
      SELECT steam_id FROM games
      WHERE steam_id = ?
    """,
            (steam_game_id,),
        ).fetchone()

    except sqlite3.Error as e:
        log.error(
            f"Error occurred fetching Steam information from games table: {type(e).__name__}: {e}"
        )
        return None

    else:
        return bool(is_steam_id_in_games)

    finally:
        conn.close()


def write_additional_steam_game_information(
    game_table_id: int, steam_game_id: int, playtime: float = 0.0
):
    conn = get_conn()
    try:
        conn.execute(
            """
      UPDATE games SET steam_id = ?
      WHERE game_table_id = ?
    """,
            (steam_game_id, game_table_id),
        )
        conn.commit()

    except sqlite3.Error as e:
        log.error(f"An operation to the games table failed: {type(e).__name__}: {e}")
        conn.rollback()
        return

    else:
        log.info(
            f"Steam ID updated in games table for game_table_id = {game_table_id}."
        )
        rel_check = create_user_game_relationship(
            game_table_id=game_table_id, hours_played=playtime
        )

        if rel_check is None:
            log.warning(
                f"Steam ID updated but user_game_relationship update failed for game_table_id = {game_table_id}"
            )

    finally:
        conn.close()


# def main():
#  steam_games = get_steam_info()
#
#  for steam_game in steam_games:
#    steam_game_name = steam_game.get('name')
#    steam_game_id = steam_game.get('appid')
#    steam_game_playtime = round((steam_game.get('playtime_forever') / 60), 2) # currently a placeholder for future use
#
#    if check_if_steam_game_exists(steam_game_id):
#      continue
#    else:
#      if igdb_id is None:
#        search_results = igdb_search()
#
#      game_processing(igdb_id)
#      write_additional_steam_game_information(steam_game_id, igdb_id)
#
# if __name__ == '__main__':
#  main()
