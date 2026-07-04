import datetime as dt
import json
import logging
import sqlite3

import requests

from config import (
    GAMEPASS_PLATFORMS,
    GAMEPASS_TIERS,
    catalog_of_ids_url,
    catalog_of_titles_url,
    get_conn,
)
from igdb import IGDB_GAMES_ENDPOINT, game_processing, header

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

log = logging.getLogger(__name__)


def create_bigId_string(
    sigl: str, platform: str, tier_code: str, url: str = catalog_of_ids_url
) -> str:
    return (
        url
        + "id="
        + sigl
        + "&language=en-us&market=US&platformContext="
        + platform
        + "&subscriptionContext="
        + tier_code
    )


def get_bigIds() -> dict:
    try:
        consoles = {
            platform: {tier: [] for tier in GAMEPASS_TIERS}
            for platform in GAMEPASS_PLATFORMS
        }

        for tier in GAMEPASS_TIERS:
            sigl = GAMEPASS_TIERS.get(tier).get("sigl")
            tier_code = GAMEPASS_TIERS.get(tier).get("tier_code")

            for platform in GAMEPASS_PLATFORMS:
                chk_bigID_string = create_bigId_string(
                    sigl=sigl, platform=platform, tier_code=tier_code
                )

                if chk_bigID_string:
                    response = requests.get(chk_bigID_string)
                else:
                    log.error("Failed to create gamepass API search string for bigId.")
                    return {}

                log.debug(
                    f"Response Status Code: {response.status_code} | URL: {response.url} | Time: {response.elapsed.total_seconds()}s | Body Preview: {response.text[:200]}"
                )
                response.raise_for_status()

                responses_of_bigIds = response.json()

                for bigId_response in responses_of_bigIds:
                    if bigId_response.get("id"):
                        consoles.get(platform).get(tier).append(
                            bigId_response.get("id")
                        )
                    else:
                        log.debug(f"Failed to obtain bigID for {bigId_response}")
                        continue

    except requests.RequestException as e:
        log.error(f"Gamepass request failed: {type(e).__name__}: {e}")
        return {}

    except json.JSONDecodeError as e:
        log.error(f"JSON Decoding failed: {e}")
        return {}

    else:
        log.info("Xbox Gamepass big_Ids obtained")
        return consoles


def create_master_set(consoles: dict) -> list:
    master_set = set()

    for platform in GAMEPASS_PLATFORMS:
        for tier in GAMEPASS_TIERS:
            master_set.update(consoles.get(platform).get(tier))

    log.info("Conversion from master_set dictionary to list successful.")
    return list(master_set)


def add_to_gamepass_table(master_set: list):
    conn = get_conn()

    try:
        list_size = 100
        chunked_list = [
            master_set[i : i + list_size] for i in range(0, len(master_set), list_size)
        ]

        for chunk in chunked_list:
            list_str = ",".join(chunk)

            response = requests.get(
                catalog_of_titles_url
                + "bigIds="
                + list_str
                + "&market=US&languages=en-us"
            )
            log.debug(
                f"Response Status Code: {response.status_code} | URL: {response.url} | Time: {response.elapsed.total_seconds()}s | Body Preview: {response.text[:200]}"
            )
            response.raise_for_status()

            names_query = response.json()
            products = names_query["Products"]

    except requests.RequestException as e:
        log.error(f"Xbox Gamepass request failed: {type(e).__name__}: {e}")
        return

    except json.JSONDecodeError as e:
        log.error(f"JSON Decoding failed: {e}")
        return

    else:
        for product in products:
            try:
                game_name = product["LocalizedProperties"][0]["ProductTitle"]
                gamepass_id = product["ProductId"]

                conn.execute(
                    """
                    INSERT OR IGNORE INTO gamepass_catalog (gamepass_id, game_title)
                    VALUES (?, ?)
                """,
                    (gamepass_id, game_name),
                )

            except sqlite3.Error as e:
                log.error(
                    f"An operation to the gamepass_catalog table failed for {game_name}: {type(e).__name__}: {e}"
                )
                continue

        conn.commit()

    finally:
        conn.close()


def update_with_tiers(consoles: dict):
    conn = get_conn()

    try:
        for platform in GAMEPASS_PLATFORMS:
            if platform == "ConsoleGen8" or platform == "ConsoleGen8;ConsoleGen9":
                continue

            for tier in GAMEPASS_TIERS:
                for bigId in consoles[platform][tier]:
                    try:
                        id_check_tuple = conn.execute(
                            """
                            SELECT gamepass_id FROM gamepass_catalog
                            WHERE gamepass_id = ?
                        """,
                            (bigId,),
                        ).fetchone()

                        id_check = id_check_tuple[0] if id_check_tuple else None

                        if id_check:
                            conn.execute(
                                f"""
                                UPDATE gamepass_catalog SET 
                                    active_on_gamepass = 1,
                                    {tier} = 1
                                WHERE gamepass_id = ?
                            """,
                                (id_check,),
                            )
                        else:
                            log.info(
                                f"bigId = {bigId} not found in gamepass_catalog, no updates performed."
                            )
                            continue

                    except sqlite3.Error:
                        log.error(
                            f"An operation to gamepass_catalog failed for bigId = {bigId}"
                        )
                        continue
        
        conn.commit()

    except Exception as e:
        log.error(f"An error has occurred during the update_with_tiers operation. {type(e).__name__}: {e}")
        return

    finally:
        conn.close()


def add_to_games_table():
    conn = get_conn()
    try:
        gamepass_items = conn.execute("""
            SELECT gamepass_id, game_title
            FROM gamepass_catalog
        """).fetchall()

    except sqlite3.Error:
        log.error("There was an error fetching data from gamepass_catalog.")
        return

    finally:
        conn.close()

    for gamepass_id, game_title in gamepass_items:
        try:
            body = f'fields external_games.name, external_games.uid; search "{game_title}";'
            response = requests.post(IGDB_GAMES_ENDPOINT, headers=header, data=body)

            log.debug(
                f"Response Status Code: {response.status_code} | URL: {response.url} | Time: {response.elapsed.total_seconds()}s | Body Preview: {response.text[:200]}"
            )
            response.raise_for_status()

            search_results = response.json()

        except requests.RequestException as e:
            log.error(f"IGDB request failed: {type(e).__name__}: {e}")
            continue

        except json.JSONDecodeError as e:
            log.error(f"JSON Decoding failed: {e}")
            continue

        else:
            for search_result in search_results:
                if search_result.get("external_games"):
                    for external_game in search_result.get("external_games"):
                        try:
                            conn = get_conn()
                            already_added = conn.execute(
                                """
                                SELECT gamepass_id FROM games WHERE gamepass_id = ?
                            """,
                                (gamepass_id,),
                            ).fetchone()

                            if already_added:
                                log.debug(
                                    f"Gamepass information already exists in games table for {gamepass_id}"
                                )
                                continue

                            if external_game.get("uid") == gamepass_id:
                                igdb_id = search_result.get("id")
                                chk_igdb = conn.execute(
                                    """
                                    SELECT igdb_id FROM games WHERE igdb_id = ?
                                """,
                                    (igdb_id,),
                                ).fetchone()

                                if not chk_igdb:
                                    game_table_id = game_processing(igdb_id=igdb_id)

                                    if not game_table_id:
                                        log.error(
                                            f"game_processing for igdb_id = {igdb_id} failed to provide a game_table_id"
                                        )
                                        continue
                                    else:
                                        conn.execute(
                                            """
                                            UPDATE games SET gamepass_id = ? WHERE game_table_id = ?
                                        """,
                                            (gamepass_id, game_table_id),
                                        )
                                        conn.commit()

                        except sqlite3.Error as e:
                            log.error(
                                f"There was an issue while interacting with the games table in the database. {type(e).__name__}: {e}"
                            )
                            continue

                        finally:
                            conn.close()

                else:
                    log.warning(
                        f"External game information not found for {game_title}."
                    )
                    continue


def create_gamepass_user_relationship():
    conn = get_conn()

    try:
        today = dt.datetime.now().date().isoformat()

        gamepass_game_table_ids = conn.execute("""
            SELECT game_table_id
            FROM games
            WHERE gamepass_id IS NOT NULL
        """).fetchall()

    except sqlite3.Error as e:
        log.error(
            f"There was an issue operating on the games table. {type(e).__name__}: {e}"
        )
        return

    else:
        for game_table_id in gamepass_game_table_ids:
            try:
                if conn.execute(
                    """
                    SELECT relationship_id
                    FROM user_game_relationship
                    WHERE game_table_id = ?
                """,
                    (game_table_id,),
                ).fetchone():
                    continue

                conn.execute(
                    """
                    INSERT OR IGNORE INTO user_game_relationship (
                        game_table_id,
                        catalog_status,
                        date_added,         
                    )
                    VALUES (?, ?, ?)
                """,
                    (game_table_id, "Xbox Gamepass", today),
                )

            except sqlite3.Error as e:
                log.error(
                    f"There was an issue operating on the user_game_relationship table for game_table_id = {id}. {type(e).__name__}: {e}"
                )
                continue

            else:
                conn.commit()

    finally:
        conn.close()


def main():
    consoles = get_bigIds()
    master_set = create_master_set(consoles)
    add_to_gamepass_table(master_set)
    update_with_tiers(consoles)
    add_to_games_table()
    create_gamepass_user_relationship()


if __name__ == "__main__":
    main()
