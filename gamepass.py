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
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("games.log"),
    ],
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
            log.debug(f"Beginning {tier} loop of GAMEPASS_TIERS get_bigIds()")
            sigl = GAMEPASS_TIERS.get(tier).get("sigl")
            tier_code = GAMEPASS_TIERS.get(tier).get("tier_code")

            for platform in GAMEPASS_PLATFORMS:
                log.debug(f"Beginning {platform} loop of GAMEPASS_PLATFORMS")
                chk_bigID_string = create_bigId_string(
                    sigl=sigl, platform=platform, tier_code=tier_code
                )

                if chk_bigID_string:
                    log.debug(
                        f"bid_ID_string created successfully for tier = {tier} and platform = {platform}"
                    )
                    response = requests.get(chk_bigID_string)
                else:
                    log.error("Failed to create gamepass API search string for bigId.")
                    return {}

                log.debug(
                    f"Gamepass Response Status Code: {response.status_code} | URL: {response.url} | Time: {response.elapsed.total_seconds()}s | Body Preview: {response.text[:200]}"
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

                log.debug(f"Completed {platform} loop of GAMEPASS_PLATFORMS")

            log.debug(f"Completed {tier} loop of GAMEPASS_TIERS get_bigIds()")

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
            log.debug(
                f"Updating master_set for platform = {platform} and tier = {tier}"
            )
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
        all_products = []

        for i, chunk in enumerate(chunked_list):
            log.debug(f"{i + 1} of {len(chunked_list)} started with {len(chunk)} items")
            list_str = ",".join(chunk)

            response = requests.get(
                catalog_of_titles_url
                + "bigIds="
                + list_str
                + "&market=US&languages=en-us"
            )
            log.debug(
                f"{i + 1} of {len(chunked_list)} Received - Response Status Code: {response.status_code} | URL: {response.url} | Time: {response.elapsed.total_seconds()}s | Body Preview: {response.text[:200]}"
            )
            response.raise_for_status()

            names_query = response.json()
            products = names_query["Products"]

            all_products.extend(
                [
                    {
                        "game_name": product["LocalizedProperties"][0]["ProductTitle"],
                        "gamepass_id": product["ProductId"],
                    }
                    for product in products
                ]
            )

            log.debug(
                f"{i + 1} of {len(chunked_list)} completed. Total items: {len(all_products)}"
            )

    except requests.RequestException as e:
        log.error(f"Xbox Gamepass request failed: {type(e).__name__}: {e}")
        return

    except json.JSONDecodeError as e:
        log.error(f"JSON Decoding failed: {e}")
        return

    else:
        for i, product in enumerate(all_products):
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO gamepass_catalog (gamepass_id, game_title)
                    VALUES (?, ?)
                """,
                    (product.get("gamepass_id"), product.get("game_name")),
                )

            except sqlite3.Error as e:
                log.error(
                    f"An operation to the gamepass_catalog table failed for {product.get('game_name')}: {type(e).__name__}: {e}"
                )
                continue

            else:
                log.debug(
                    f"Product {i + 1} of {len(all_products)} added to gamepass_catalog successfully."
                )

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
        log.error(
            f"An error has occurred during the update_with_tiers operation. {type(e).__name__}: {e}"
        )
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
            body = f'fields external_games.name, external_games.uid, external_games.external_game_source.name; search "{game_title}";'
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
                    steam_id = None

                    for external_game in search_result.get("external_games"):
                        try:
                            conn = get_conn()
                            ext_game_src = external_game.get("external_game_source")

                            if ext_game_src and ext_game_src.get("id") == 1:
                                steam_id = external_game.get("uid")

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
                                        if not steam_id:
                                            conn.execute(
                                                """
                                                UPDATE games SET gamepass_id = ? WHERE game_table_id = ?
                                            """,
                                                (gamepass_id, game_table_id),
                                            )
                                            conn.commit()
                                        else:
                                            conn.execute(
                                                """
                                                UPDATE games SET gamepass_id = ?, steam_id = ? WHERE game_table_id = ?
                                            """,
                                                (gamepass_id, steam_id, game_table_id),
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
            game_table_id = game_table_id[0]
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
                        date_added         
                    )
                    VALUES (?, ?, ?)
                """,
                    (game_table_id, "Xbox Gamepass", today),
                )

            except sqlite3.Error as e:
                log.error(
                    f"There was an issue operating on the user_game_relationship table for game_table_id = {game_table_id}. {type(e).__name__}: {e}"
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
