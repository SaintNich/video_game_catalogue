import datetime as dt
import json
import logging
import sqlite3

import requests

from access_token import create_header
from config import IGDB_GAMES_ENDPOINT, get_conn

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="games.log",
)

log = logging.getLogger(__name__)
header = create_header()


def igdb_search(igdb_id: int = None, web_input: str = None) -> list:
    try:
        if igdb_id is None:
            title_search = web_input
            log.info(f"IGDB search beginning for game title: {title_search}")

            body = (
                f'fields name, first_release_date; search "{title_search}"; limit 50;'
            )
            response = requests.post(IGDB_GAMES_ENDPOINT, headers=header, data=body)

        else:
            log.info(f"IGDB search beginning for IGDB ID# {igdb_id}")

            body = (
                f"fields name, first_release_date; where id = {igdb_id}; sort id asc;"
            )
            response = requests.post(IGDB_GAMES_ENDPOINT, headers=header, data=body)

        log.debug(
            f"Response Status Code: {response.status_code} | URL: {response.url} | Time: {response.elapsed.total_seconds()}s | Body Preview: {response.text[:200]}"
        )
        response.raise_for_status()
        search_results = response.json()

    except requests.RequestException as e:
        log.error(f"IGDB request failed: {type(e).__name__}: {e}")
        return []

    except json.JSONDecodeError as e:
        log.error(f"JSON Decoding failed: {e}")
        return []

    else:
        log.info(
            f"IGDB search completed successfully. Number of results received: {len(search_results)}"
        )
        return search_results


def full_game_info(igdb_id: int, search_results: list = None) -> dict:
    try:
        if search_results is None:
            srch_results = igdb_search(igdb_id=igdb_id)

            if srch_results:
                srch_result = srch_results[0]
                igdb_id = srch_result.get("id")
            else:
                log.warning(
                    "igdb_search() returned an empty list, srch_results not available."
                )
                return {}

        body = f"fields age_ratings.synopsis, age_ratings.organization.name, age_ratings.rating_category.rating, age_ratings.rating_content_descriptions.description, alternative_names.name, artworks.image_id, artworks.url, collections.games.name, collections.name, cover.image_id, cover.url, dlcs.name, expanded_games.name, expansions.name, external_games.name, external_games.uid, external_games.external_game_source.name, first_release_date, forks.name, game_modes.slug, game_status.status, game_type.type, genres.slug, involved_companies.company.name, involved_companies.developer, involved_companies.porting, involved_companies.publisher, involved_companies.supporting, multiplayer_modes.campaigncoop, multiplayer_modes.dropin, multiplayer_modes.lancoop, multiplayer_modes.offlinecoop, multiplayer_modes.offlinemax, multiplayer_modes.onlinecoop, multiplayer_modes.onlinemax, multiplayer_modes.splitscreen, name, parent_game.name, platforms.abbreviation, platforms.alternative_name, platforms.name, remakes.name, remasters.name, standalone_expansions.name, storyline, summary, themes.slug, version_parent.name, version_title, websites.url, websites.type.type; where id = {igdb_id}; sort id asc;"

        response = requests.post(IGDB_GAMES_ENDPOINT, headers=header, data=body)
        log.debug(
            f"Response Status Code: {response.status_code} | URL: {response.url} | Time: {response.elapsed.total_seconds()}s | Body Preview: {response.text[:200]}"
        )
        response.raise_for_status()
        full_game_results = response.json()

    except requests.RequestException as e:
        log.error(f"IGDB request failed: {type(e).__name__}: {e}")
        return {}

    except json.JSONDecodeError as e:
        log.error(f"JSON Decoding failed: {e}")
        return {}

    else:
        full_game_result = full_game_results[0]
        log.info("IGDB full game info pulled successfully.")
        return full_game_result


def update_games(full_game_result: dict) -> int:
    conn = get_conn()

    try:
        igdb_id = full_game_result.get("id")
        title = full_game_result.get("name")
        alt_titles = (
            [name.get("name") for name in full_game_result.get("alternative_names")]
            if full_game_result.get("alternative_names")
            else None
        )
        cover = (
            full_game_result.get("cover").get("url")
            if full_game_result.get("cover")
            else None
        )
        img_urls = (
            [art.get("url") for art in full_game_result.get("artworks")]
            if full_game_result.get("artworks")
            else None
        )
        summary = full_game_result.get("summary")
        story = full_game_result.get("storyline")
        release_date = full_game_result.get("first_release_date")
        game_type = (
            full_game_result.get("game_type").get("type")
            if full_game_result.get("game_type")
            else None
        )
        game_modes = (
            [mode.get("slug") for mode in full_game_result.get("game_modes")]
            if full_game_result.get("game_modes")
            else None
        )
        genres = (
            [genre.get("slug") for genre in full_game_result.get("genres")]
            if full_game_result.get("genres")
            else None
        )
        themes = (
            [theme.get("slug") for theme in full_game_result.get("themes")]
            if full_game_result.get("themes")
            else None
        )
        expansion_of = (
            full_game_result.get("parent_game").get("name")
            if full_game_result.get("parent_game")
            else None
        )

        rating_org = ""
        rating_cat = ""
        rating_desc = []

        if full_game_result.get("age_ratings"):
            for rating in full_game_result.get("age_ratings"):
                chk_rating_org = (
                    rating.get("organization").get("name")
                    if rating.get("organization")
                    else None
                )
                if chk_rating_org != "ESRB":
                    continue

                rating_org = chk_rating_org
                rating_cat = (
                    rating.get("rating_category").get("rating")
                    if rating.get("rating_category")
                    else None
                )
                rating_desc = (
                    [
                        desc.get("description")
                        for desc in rating.get("rating_content_descriptions")
                    ]
                    if rating.get("rating_content_descriptions")
                    else []
                )

        conn.execute(
            """
            INSERT OR IGNORE INTO games (
                igdb_id, 
                title,
                alt_titles,
                cover_url,
                images,
                summary,
                story,
                release_date,
                game_type,
                game_modes,
                genres,
                themes,
                expansion_of,
                age_rating_org,
                age_rating_cat,
                age_rating_desc
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                igdb_id,
                title,
                ", ".join(alt_titles) if alt_titles else None,
                cover,
                ", ".join(img_urls) if img_urls else None,
                summary,
                story,
                dt.datetime.fromtimestamp(release_date).date().isoformat()
                if release_date
                else "unknown",
                game_type,
                ", ".join(game_modes) if game_modes else None,
                ", ".join(genres) if genres else None,
                ", ".join(themes) if themes else None,
                expansion_of,
                rating_org if rating_org else None,
                rating_cat if rating_cat else None,
                ", ".join(rating_desc) if rating_desc else None,
            ),
        )
        conn.commit()

        game_table_ids = conn.execute(
            """
            SELECT game_table_id
            FROM games
            WHERE igdb_id = ?
        """,
            (full_game_result.get("id"),),
        ).fetchone()

    except sqlite3.Error as e:
        log.error(f"An operation to the games table failed: {type(e).__name__}: {e}")
        return None

    else:
        game_table_id = game_table_ids[0]
        log.info(f"Update to games table successful. Game table ID#: {game_table_id}")
        return game_table_id

    finally:
        conn.close()


def update_multiplayer(game_table_id: int, full_game_result: dict):
    conn = get_conn()
    try:
        multiplayer = full_game_result.get("multiplayer_modes")

        if multiplayer:
            log.info("Multiplayer information obtained.")
            multiplayer = multiplayer[0]
            conn.execute(
                """
                INSERT OR IGNORE INTO multiplayer_modes (
                    game_table_id, 
                    campaigncoop, 
                    dropin, 
                    lancoop, 
                    offlinecoop,
                    onlinecoop,
                    splitscreen,
                    splitscreenonline,
                    offlinemax,
                    onlinemax
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    game_table_id,
                    multiplayer.get("campaigncoop"),
                    multiplayer.get("dropin"),
                    multiplayer.get("lancoop"),
                    multiplayer.get("offlinecoop"),
                    multiplayer.get("onlinecoop"),
                    multiplayer.get("splitscreen"),
                    multiplayer.get("splitscreenonline"),
                    multiplayer.get("offlinemax"),
                    multiplayer.get("onlinemax"),
                ),
            )
            conn.commit()
        else:
            log.info("Multiplayer information not available.")
            return

    except sqlite3.Error as e:
        log.error(
            f"An operation to the multiplayer_modes table failed: {type(e).__name__}: {e}"
        )
        return None

    else:
        log.info("Update to multiplayer_modes table successful.")
        return

    finally:
        conn.close()


def update_external_sources(game_table_id: int, full_game_result: dict):
    conn = get_conn()

    try:
        if full_game_result.get("external_games"):
            log.info("External game source information obtained.")
            ext_sources = [
                {
                    "ext_uid": ext_game.get("uid"),
                    "ext_source": ext_game.get("external_game_source").get("name")
                    if ext_game.get("external_game_source")
                    else None,
                }
                for ext_game in full_game_result.get("external_games")
            ]
        else:
            ext_sources = None

        if ext_sources:
            for src in ext_sources:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO external_sources (
                        game_table_id, ext_src, ext_src_uid           
                    )
                    VALUES (?, ?, ?)
                """,
                    (game_table_id, src.get("ext_source"), src.get("ext_uid")),
                )
        else:
            log.warning("External sources information not available.")
            return

    except sqlite3.Error as e:
        log.error(
            f"An operation to the external_sources table failed: {type(e).__name__}: {e}"
        )
        conn.rollback()
        return

    except Exception as e:
        log.error(
            f"An unexpected error occurred in update_external_sources(). {type(e).__name__}: {e}"
        )
        conn.rollback()
        return

    else:
        log.info("Update to external_sources table successful")
        conn.commit()

    finally:
        conn.close()


def update_game_involved_companies(game_table_id: int, full_game_result: dict):
    conn = get_conn()

    try:
        if full_game_result.get("involved_companies"):
            log.info("Game involved company information obtained.")
            inv_comps = [
                {
                    "company_name": company.get("company").get("name")
                    if company.get("company")
                    else None,
                    "developer": company.get("developer"),
                    "porting": company.get("porting"),
                    "publisher": company.get("publisher"),
                    "supporting": company.get("supporting"),
                }
                for company in full_game_result.get("involved_companies")
            ]
        else:
            inv_comps = None

        if inv_comps:
            for co in inv_comps:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO game_involved_companies (
                        game_table_id,
                        company,
                        is_developer,
                        is_porting,
                        is_publisher,
                        is_supporting           
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        game_table_id,
                        co.get("company_name"),
                        co.get("developer"),
                        co.get("porting"),
                        co.get("publisher"),
                        co.get("supporting"),
                    ),
                )
        else:
            log.warning("Involved companies not available.")
            return

    except sqlite3.Error as e:
        log.error(
            f"An operation with the game_involved_companies table failed: {type(e).__name__}: {e}"
        )
        conn.rollback()
        return

    except Exception as e:
        log.error(
            f"An unexpected error occurred in update_game_involved_companies(). {type(e).__name__}: {e}"
        )
        conn.rollback()
        return

    else:
        log.info("Update to game_involved_companies table successful.")
        conn.commit()

    finally:
        conn.close()


def update_game_platforms(game_table_id: int, full_game_result: dict):
    conn = get_conn()

    try:
        if full_game_result.get("platforms"):
            log.info("Game platform information obtained.")
            platforms = [
                {
                    "abbr": platform.get("abbreviation"),
                    "name": platform.get("name"),
                    "alt_name": platform.get("alternative_name"),
                }
                for platform in full_game_result.get("platforms")
            ]
        else:
            platforms = None

        if platforms:
            for platform in platforms:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO game_platforms (
                        game_table_id,
                        platform,
                        platform_abbr,
                        alt_platform_name           
                    )
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        game_table_id,
                        platform.get("name"),
                        platform.get("abbr"),
                        platform.get("alt_name"),
                    ),
                )
        else:
            log.warning("Platform information not available.")
            return

    except sqlite3.Error as e:
        log.error(
            f"An operation to the game_platforms table failed: {type(e).__name__}: {e}"
        )
        conn.rollback()
        return

    except Exception as e:
        log.error(
            f"An unexpected error occurred in update_game_platforms(). {type(e).__name__}: {e}"
        )
        conn.rollback()
        return

    else:
        log.info("Update to game_platforms table successful.")
        conn.commit()

    finally:
        conn.close()


def update_game_websites(game_table_id: int, full_game_result: dict):
    conn = get_conn()

    try:
        if full_game_result.get("websites"):
            log.info("Game website information obtained")
            websites = [
                {
                    "type": website.get("type").get("type")
                    if website.get("type")
                    else None,
                    "url": website.get("url"),
                }
                for website in full_game_result.get("websites")
            ]
        else:
            websites = None

        if websites:
            for site in websites:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO game_websites (
                        game_table_id,
                        website_type,
                        website_url
                    )
                    VALUES (?, ?, ?)
                """,
                    (game_table_id, site.get("type"), site.get("url")),
                )
        else:
            log.warning("Website information not available.")
            return

    except sqlite3.Error as e:
        log.error(
            f"An operation to the game_websites table failed: {type(e).__name__}: {e}"
        )
        conn.rollback()
        return

    except Exception as e:
        log.error(
            f"An unexpected error occurred in update_game_websites(). {type(e).__name__}: {e}"
        )
        conn.rollback()
        return

    else:
        log.info("Update to game_websites table successful.")
        conn.commit()

    finally:
        conn.close()


def update_game_series(game_table_id: int, full_game_result: dict):
    conn = get_conn()

    try:
        if full_game_result.get("collections"):
            log.info("Series information obtained.")
            collections = [
                {
                    "collection_name": collection.get("name"),
                    "games": [game.get("name") for game in collection.get("games")],
                }
                for collection in full_game_result.get("collections")
            ]
        else:
            collections = None

        if collections:
            for collection in collections:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO game_series (
                        game_table_id,
                        series,
                        total_games_in_series           
                    )
                    VALUES (?, ?, ?)
                """,
                    (
                        game_table_id,
                        collection.get("collection_name"),
                        len(collection.get("games")),
                    ),
                )
        else:
            log.info("Series information not available or doesn't exist.")
            return

    except sqlite3.Error as e:
        log.error(
            f"An operation to the game_series table failed: {type(e).__name__}: {e}"
        )
        conn.rollback()
        return

    except Exception as e:
        log.error(
            f"An unexpected error occurred in update_game_series(). {type(e).__name__}: {e}"
        )
        conn.rollback()
        return

    else:
        log.info("Update to game_series table successful.")
        conn.commit()

    finally:
        conn.close()


def game_processing(igdb_id: int) -> int:
    full_game_result = full_game_info(igdb_id=igdb_id)

    if full_game_result:
        game_table_id = update_games(full_game_result=full_game_result)

        if game_table_id:
            update_multiplayer(
                game_table_id=game_table_id, full_game_result=full_game_result
            )
            update_external_sources(
                game_table_id=game_table_id, full_game_result=full_game_result
            )
            update_game_involved_companies(
                game_table_id=game_table_id, full_game_result=full_game_result
            )
            update_game_platforms(
                game_table_id=game_table_id, full_game_result=full_game_result
            )
            update_game_websites(
                game_table_id=game_table_id, full_game_result=full_game_result
            )
            update_game_series(
                game_table_id=game_table_id, full_game_result=full_game_result
            )

            return game_table_id
        else:
            log.warning("game_table_id not available.")
            return None
    else:
        log.warning("full_game_result not available.")
        return None
