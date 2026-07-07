import ast
import datetime as dt
import logging
import os
import sqlite3

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from config import get_conn
from gamepass import (
    add_to_gamepass_table,
    add_to_games_table,
    create_gamepass_user_relationship,
    create_master_set,
    get_bigIds,
    update_with_tiers,
)
from hltb import add_hltb_info, get_hltb_info
from igdb import game_processing, igdb_search
from steam import (
    check_if_steam_game_exists,
    get_steam_info,
    write_additional_steam_game_information,
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

load_dotenv()

log = logging.getLogger(__name__)
app = Flask(__name__)
app.secret_key = os.getenv("secret_key")


@app.route("/")
def index():
    conn = get_conn()

    try:
        catalog_data = conn.execute("""
            SELECT
                g.game_table_id,
                g.title,
                g.release_date,
                g.expansion_of,
                s.series,
                g.game_modes
            FROM games g
            LEFT JOIN game_series s
            ON g.game_table_id = s.game_table_id                          
            GROUP BY g.game_table_id, g.title, g.release_date
        """).fetchall()

    except sqlite3.Error as e:
        log.error(f"An error occured with the database: {type(e).__name}: {e}")
        return

    else:
        log.info("Successfully obtained 'catalog_data' from database.")
        catalog_table = [
            {
                "game_table_id": game_table_id,
                "title": title,
                "release_date": release_date,
                "expansion_of": expansion_of,
                "series_name": series_name,
                "game_modes": game_modes,
            }
            for game_table_id, title, release_date, expansion_of, series_name, game_modes in catalog_data
        ]

        return render_template("index.html", catalog_table=catalog_table)

    finally:
        conn.close()


@app.route("/game_search", methods=["GET", "POST"])
def game_search():
    if request.method == "POST":
        game_search = request.form.get("game_search")
        search_results_raw = igdb_search(web_input=game_search)

        if not search_results_raw:
            flash("IGDB found no results, try again", "info")
            return redirect(url_for("index"))

        search_results = []

        for search_result in search_results_raw:
            try:
                search_results.append(
                    {
                        "game_title": search_result.get("name"),
                        "release_year": dt.datetime.fromtimestamp(
                            search_result.get("first_release_date")
                        ).year
                        if search_result.get("first_release_date")
                        else "unknown",
                        "igdb_id": search_result.get("id"),
                    }
                )

            except (ValueError, OSError, OverflowError) as e:
                log.warning(f"Error: {type(e).__name__}: {e}")
                continue

            else:
                return render_template("results.html", search_results=search_results)
    else:
        return render_template("game_search.html")


@app.route("/game_selection", methods=["GET", "POST"])
def game_selection():
    if request.method == "POST":
        try:
            game_selection = tuple(request.form.get("game_selection").split(","))
            igdb_id, game_title = game_selection
            igdb_id = int(igdb_id)
            steam_game_id = int(request.form.get("steam_game_id"))
            steam_game_playtime = float(request.form.get("steam_game_playtime"))
            log.info(
                f"IGDB ID#: {igdb_id} | Game Title: {game_title} | Steam Game ID#: {steam_game_id} | Steam Playtime: {steam_game_playtime}"
            )

        except TypeError as e:
            log.error(f"Invalid type {type(e).__name__}: {e}")
            flash(
                "Something went wrong during game selection, please try again.", "error"
            )
            return redirect(url_for("index"))

        except ValueError as e:
            log.error(f"Improper value submitted: {type(e).__name__}: {e}")
            flash(
                "Something went wrong during game selection, please try again.", "error"
            )
            return redirect(url_for("index"))

        else:
            processed_game = game_processing(igdb_id=igdb_id)
            hltb_results = get_hltb_info(game_name=game_title)

            if processed_game:
                if steam_game_id:
                    write_additional_steam_game_information(
                        game_table_id=processed_game,
                        steam_game_id=steam_game_id,
                        playtime=steam_game_playtime,
                    )
                else:
                    log.info(
                        "Steam game information not available or doesn't exist, no steam data written."
                    )

                if hltb_results:
                    log.info("HLTB results found")
                    return render_template(
                        "processing.html",
                        hltb_results=hltb_results,
                        game_table_id=processed_game,
                    )
                else:
                    log.info("No results found for HLTB search, table not updated.")
                    flash("HLTB search found no results.", "info")
                    return redirect(url_for("index"))
            else:
                log.warning(f"Data not returned from game_processing({igdb_id})")
                flash("Failed to process game, try again.", "error")
                return redirect(url_for("index"))
    else:
        return redirect(url_for("index"))


@app.route("/processing", methods=["GET", "POST"])
def processing():
    if request.method == "POST":
        try:
            hltb_selection = tuple(request.form.get("hltb_selection").split(", "))
            (
                hltb_id,
                hltb_main_story,
                hltb_main_extras,
                hltb_completionist,
                hltb_all_styles,
            ) = hltb_selection
            game_table_id = int(request.form.get("game_table_id"))

            chk_hltb_info = add_hltb_info(
                hltb_id=hltb_id,
                game_table_id=game_table_id,
                hltb_main_story=hltb_main_story,
                hltb_main_extras=hltb_main_extras,
                hltb_completionist=hltb_completionist,
                hltb_all_styles=hltb_all_styles,
            )

        except ValueError as e:
            log.error(f"Improper value submitted: {type(e).__name__}: {e}")
            flash("Something went wrong during processing, please try again.", "error")
            return redirect(url_for("index"))

        except TypeError as e:
            log.error(f"Invalid type {type(e).__name__}: {e}")
            flash("Something went wrong during processing, please try again.", "error")
            return redirect(url_for("index"))

        else:
            if chk_hltb_info:
                log.info("HowLongToBeat table updated")
            else:
                log.info(f"No HowLongToBeat data for game_table_id {game_table_id}")
                flash(
                    "HowLongToBeat table not updated, no information provided.", "info"
                )
            return redirect(url_for("index"))
    else:
        return redirect(url_for("index"))


@app.route("/steam_sync", methods=["GET", "POST"])
def steam_sync():
    if request.method == "POST":
        steam_games = get_steam_info()
        steam_games_not_in_db = []

        if steam_games:
            log.info("Information for steam_sync obtained successfully.")
            for steam_game in steam_games:
                steam_game_name = steam_game.get("name")
                steam_game_id = steam_game.get("appid")
                steam_game_playtime = (
                    round((steam_game.get("playtime_forever") / 60), 2)
                    if steam_game.get("playtime_forever")
                    else 0.0
                )
                steam_chk = check_if_steam_game_exists(steam_game_id=steam_game_id)

                if steam_chk is None:
                    flash("Unable to retrieve Steam library.", "error")
                    return redirect(url_for("index"))

                if steam_chk:
                    continue
                else:
                    steam_games_not_in_db.append(
                        {
                            "steam_game_id": steam_game_id,
                            "steam_game_name": steam_game_name,
                            "steam_game_playtime": steam_game_playtime,
                        }
                    )

            return render_template(
                "steam_review.html", steam_games_not_in_db=steam_games_not_in_db
            )
        else:
            log.warning("No steam_games returned from get_steam_info.")
            flash("Error attempting to retrieve Steam library.", "error")
            return redirect(url_for("index"))
    else:
        return redirect(url_for("index"))


@app.route("/steam_search", methods=["GET", "POST"])
def steam_search():
    if request.method == "POST":
        if "steam_selection" in request.form:
            log.debug("'steam_selection' found")
            try:
                steam_selection = tuple(request.form.get("steam_selection").split(", "))
                steam_game_id, steam_game_name, steam_game_playtime = steam_selection
                log.info(
                    f"Steam Game ID: {steam_game_id} | Steam Game Name: {steam_game_name} | Steam Playtime: {steam_game_playtime}"
                )

            except ValueError as e:
                log.error(f"Improper value submitted: {type(e).__name__}: {e}")
                flash("Something went wrong with those details, try again", "error")
                return redirect(url_for("index"))

            else:
                return render_template(
                    "steam_search.html",
                    steam_selection=steam_selection,
                    steam_game_name=steam_game_name,
                    steam_game_id=steam_game_id,
                    steam_game_playtime=steam_game_playtime,
                )
        else:
            log.debug("'steam_selection' not found")
            steam_search = request.form.get("steam_search")
            steam_game_id = request.form.get("steam_game_id")
            steam_game_playtime = request.form.get("steam_game_playtime")
            search_results_raw = igdb_search(web_input=steam_search)

            if not search_results_raw:
                flash("IGDB found no results, try again", "info")
                return redirect(url_for("index"))

            search_results = []

            for search_result in search_results_raw:
                try:
                    name = search_result.get("name")
                    release_year = (
                        dt.datetime.fromtimestamp(
                            search_result.get("first_release_date")
                        ).year
                        if search_result.get("first_release_date")
                        else "unknown"
                    )
                    igdb_id = search_result.get("id")
                    log.debug(
                        f"Game Name: {name} | Release Year: {release_year} | IGDB ID#: {igdb_id}"
                    )

                except (ValueError, OSError, OverflowError) as e:
                    log.warning(f"Error: {type(e).__name__}: {e}")
                    continue

                else:
                    search_results.append(
                        {
                            "game_title": name,
                            "release_year": release_year,
                            "igdb_id": igdb_id,
                        }
                    )

            return render_template(
                "results.html",
                search_results=search_results,
                steam_game_id=steam_game_id,
                steam_game_playtime=steam_game_playtime,
            )

    else:
        return redirect(url_for("index"))


@app.route("/gamepass_update", methods=["GET", "POST"])
def gamepass_update():
    if request.method == "POST":
        consoles = get_bigIds()

        if consoles:
            master_set = create_master_set(consoles)

            if master_set:
                add_to_gamepass_table(master_set)
                update_with_tiers(consoles)
                add_to_games_table()
                create_gamepass_user_relationship()
                return redirect(url_for("index"))
            else:
                log.error("Master set not provided from gamepass module")
                flash("An error occurred during gamepass update", "error")
                return redirect(url_for("index"))
        else:
            flash("An error occurred during gamepass update", "error")
            return redirect(url_for("index"))

    else:
        return redirect(url_for("index"))


@app.route("/game_details/<int:game_table_id>", methods=["GET", "POST"])
def game_details(game_table_id):
    if request.method == "POST":
        conn = get_conn()

        try:
            core_game_info = conn.execute(
                """
                SELECT 
                    title, 
                    alt_titles,
                    cover_url,
                    summary,
                    story,
                    release_date,      
                    CASE
                        WHEN controller_supported = 1 THEN 'Controller Supported'
                        WHEN controller_supported = 0 THEN 'Controller Not Supported'
                        ELSE NULL
                    END AS controller_supported,
                    game_type,
                    game_modes,
                    genres,
                    themes,
                    age_rating_org,
                    age_rating_cat,
                    age_rating_desc,
                    expansion_of
                FROM games
                WHERE game_table_id = ?
            """,
                (game_table_id,),
            ).fetchone()

            relationship_info = conn.execute(
                """
                SELECT
                    catalog_status,
                    date_main_completed,
                    date_completed,
                    hours_played,
                    rating,
                    user_notes
                FROM user_game_relationship
                WHERE game_table_id = ?
            """,
                (game_table_id,),
            ).fetchone()

            multiplayer_info = conn.execute(
                """
                SELECT
                    campaigncoop,
                    dropin,
                    lancoop,
                    offlinecoop,
                    onlinecoop,
                    splitscreen,
                    splitscreenonline,
                    offlinemax,
                    onlinemax
                FROM multiplayer_modes
                WHERE game_table_id = ?
            """,
                (game_table_id,),
            ).fetchone()

            ext_src_info = conn.execute(
                """
                SELECT
                    ext_src,
                    ext_src_uid
                FROM external_sources
                WHERE game_table_id = ?
            """,
                (game_table_id,),
            ).fetchall()

            company_info = conn.execute(
                """
                SELECT
                    company,
                    is_developer,
                    is_porting,
                    is_publisher,
                    is_supporting
                FROM game_involved_companies
                WHERE game_table_id = ?
            """,
                (game_table_id,),
            ).fetchall()

            platform_info = conn.execute(
                """
                SELECT platform
                FROM game_platforms
                WHERE game_table_id = ?
            """,
                (game_table_id,),
            ).fetchall()

            website_info = conn.execute(
                """
                SELECT
                    website_type,
                    website_url
                FROM game_websites
                WHERE game_table_id = ?
            """,
                (game_table_id,),
            ).fetchall()

            series_info = conn.execute(
                """
                SELECT 
                    series,
                    total_games_in_series
                FROM game_series
                WHERE game_table_id = ?
            """,
                (game_table_id,),
            ).fetchall()

            hltb_info = conn.execute(
                """
                SELECT
                    main_story,
                    main_extras,
                    completionist,
                    all_play_styles
                FROM hltb_data
                WHERE game_table_id = ?
            """,
                (game_table_id,),
            ).fetchone()

            user_platform_own_info = conn.execute(
                """
                SELECT gp.platform
                FROM game_platforms gp
                JOIN user_platform_own u
                ON gp.platform_id = u.platform_id
                AND u.relationship_id = (
                    SELECT relationship_id
                    FROM user_game_relationship
                    WHERE game_table_id = ?
                )
                WHERE gp.game_table_id = ?
            """,
                (game_table_id, game_table_id),
            ).fetchall()

            user_played_on_info = conn.execute(
                """
                SELECT gp.platform
                FROM game_platforms gp
                JOIN user_played_on u
                ON gp.platform_id = u.platform_id
                AND u.relationship_id = (
                    SELECT relationship_id
                    FROM user_game_relationship
                    WHERE game_table_id = ?
                )
                WHERE gp.game_table_id = ?
            """,
                (game_table_id, game_table_id),
            ).fetchall()

        except sqlite3.Error as e:
            log.error(f"An error occurred during database operation. {type(e).__name__}: {e}")
            flash("Something went wrong processing game details, try again.", "error")
            return redirect(url_for("index"))

        finally:
            conn.close()

        if core_game_info:
            core_game_dict = {
                "game_title": core_game_info[0],
                "alt_titles": core_game_info[1],
                "cover_url": core_game_info[2],
                "summary": core_game_info[3],
                "story": core_game_info[4],
                "release_date": core_game_info[5],
                "controller_supported": core_game_info[6],
                "game_type": core_game_info[7],
                "game_modes": core_game_info[8],
                "genres": core_game_info[9],
                "themes": core_game_info[10],
                "age_rating_org": core_game_info[11],
                "age_rating_cat": core_game_info[12],
                "age_rating_desc": core_game_info[13],
                "expansion_of": core_game_info[14],
            }
        else:
            core_game_dict = {}

        if relationship_info:
            relationship_dict = {
                "catalog_status": relationship_info[0],
                "date_main_completed": relationship_info[1],
                "date_completed": relationship_info[2],
                "hours_played": relationship_info[3],
                "rating": relationship_info[4],
                "user_notes": relationship_info[5],
            }
        else:
            relationship_dict = {}

        if multiplayer_info:
            multiplayer_dict = {
                "campaigncoop": multiplayer_info[0],
                "dropin": multiplayer_info[1],
                "lancoop": multiplayer_info[2],
                "offlinecoop": multiplayer_info[3],
                "onlinecoop": multiplayer_info[4],
                "splitscreen": multiplayer_info[5],
                "splitscreenonline": multiplayer_info[6],
                "offlinemax": multiplayer_info[7],
                "onlinemax": multiplayer_info[8],
            }
        else:
            multiplayer_dict = {}

        if ext_src_info:
            ext_src_dict = [{"ext_src": src[0], "ext_src_uid": src[1]} for src in ext_src_info]
        else:
            ext_src_dict = []

        if company_info:
            company_dict = [
                {
                    "company": row[0],
                    "is_developer": row[1],
                    "is_porting": row[2],
                    "is_puublisher": row[3],
                    "is_supporting": row[4],
                }
                for row in company_info
            ]
        else:
            company_dict = []

        if platform_info:
            platform_dict = [{"platform": row[0]} for row in platform_info]
        else:
            platform_dict = []

        if website_info:
            website_dict = [
                {"website_type": row[0], "website_url": row[1]} for row in website_info
            ]
        else:
            website_dict = []

        if series_info:
            series_dict = [
                {"series_name": row[0], "total_games_in_series": row[1]} for row in series_info
            ]
        else:
            series_dict = []

        if hltb_info:
            hltb_dict = {
                "main_story": hltb_info[0],
                "main_extras": hltb_info[1],
                "completionist": hltb_info[2],
                "all_play_styles": hltb_info[3],
            }
        else:
            hltb_dict = {}

        if user_platform_own_info:
            user_platform_own_dict = [{"owned": row[0]} for row in user_platform_own_info]
        else:
            user_platform_own_dict = []

        if user_played_on_info:
            user_played_on_dict = [{"played": row[0]} for row in user_played_on_info]
        else:
            user_played_on_dict = []

        return render_template(
            "game_details.html",
            game_table_id=game_table_id,
            core_game_dict=core_game_dict,
            relationship_dict=relationship_dict,
            multiplayer_dict=multiplayer_dict,
            ext_src_dict=ext_src_dict,
            company_dict=company_dict,
            platform_dict=platform_dict,
            website_dict=website_dict,
            series_dict=series_dict,
            hltb_dict=hltb_dict,
            user_platform_own_dict=user_platform_own_dict,
            user_played_on_dict=user_played_on_dict,
        )
    else:
        return redirect(url_for("index"))


@app.route("/game_details_form", methods=["GET", "POST"])
def game_details_form():
    if request.method == "POST":
        conn = get_conn()
        try:
            game_table_id = int(request.form.get("game_table_id"))
            platform_dict = ast.literal_eval(request.form.get("platform_dict"))

            fetch_cur_relationship_values = conn.execute(
                """
                SELECT
                    catalog_status,
                    date_main_completed,
                    date_completed,
                    hours_played,
                    rating,
                    user_notes
                FROM user_game_relationship
                WHERE game_table_id = ?
            """,
                (game_table_id,),
            ).fetchone()

            if fetch_cur_relationship_values:
                cur_relationship_values = {
                    "catalog_status": fetch_cur_relationship_values[0],
                    "date_main_completed": fetch_cur_relationship_values[1],
                    "date_completed": fetch_cur_relationship_values[2],
                    "hours_played": fetch_cur_relationship_values[3],
                    "rating": fetch_cur_relationship_values[4],
                    "user_notes": fetch_cur_relationship_values[5],
                }
            else:
                cur_relationship_values = {}

            fetch_ownership_values = conn.execute(
                """
                SELECT
                    gp.platform,
                    upo.relationship_id
                FROM game_platforms gp
                LEFT JOIN user_platform_own upo
                ON gp.platform_id = upo.platform_id
                AND upo.relationship_id = (
                    SELECT relationship_id
                    FROM user_game_relationship
                    WHERE game_table_id =?                            
                )
                WHERE gp.game_table_id = ?
            """,
                (game_table_id, game_table_id),
            ).fetchall()

            if fetch_ownership_values:
                ownership_values = [
                    {"platform": value[0], "owned": True if value[1] else False}
                    for value in fetch_ownership_values
                ]
            else:
                ownership_values = []

            fetch_played_on_values = conn.execute(
                """
                SELECT
                    gp.platform,
                    upo.relationship_id
                FROM game_platforms gp
                LEFT JOIN user_played_on upo
                ON gp.platform_id = upo.platform_id
                AND upo.relationship_id = (
                    SELECT relationship_id
                    FROM user_game_relationship
                    WHERE game_table_id =?                            
                )
                WHERE gp.game_table_id = ?
            """,
                (game_table_id, game_table_id),
            ).fetchall()

            if fetch_played_on_values:
                played_on_values = [
                    {"platform": value[0], "played": True if value[1] else False}
                    for value in fetch_played_on_values
                ]
            else:
                played_on_values = []

        except (TypeError, ValueError, SyntaxError) as e:
            log.error(f"Improper datatype returned. {type(e).__name__}: {e}")
            flash("Something went wrong obtaining information", "error")
            return redirect(url_for("index"))
        
        except sqlite3.Error as e:
            log.error(f"An error occurred while interacting with the database. {type(e).__name__}: {e}")
            flash("Something went wrong during the database operation, please try again", "error")
            return redirect(url_for("index"))

        else:
            return render_template(
                "update_game.html",
                game_table_id=game_table_id,
                platform_dict=platform_dict,
                cur_relationship_values=cur_relationship_values,
                ownership_values=ownership_values,
                played_on_values=played_on_values,
            )
        
        finally:
            conn.close()
    else:
        return redirect(url_for("index"))


@app.route("/update_game_details", methods=["GET", "POST"])
def update_game_details():
    if request.method == "POST":
        conn = get_conn()
        try:
            if not request.form.get("game_table_id"):
                log.error("game_table_id not provided.")
                flash("Something went wrong accessing game information, try again", "error")
                return redirect(url_for("index"))
        
            game_table_id = int(request.form.get("game_table_id"))
            catalog_update = request.form.get("catalog_status")
            date_main_update = request.form.get("date_main")
            date_full_update = request.form.get("date_full")
            hours_update = (
                float(request.form.get("hours_played"))
                if request.form.get("hours_played")
                else 0.0
            )
            rating_update = (
                float(request.form.get("rating")) if request.form.get("rating") else 0.0
            )
            notes_update = request.form.get("user_notes")
            owned_platforms = request.form.getlist("owned_platform")
            played_platforms = request.form.getlist("played_platform")
            controller_support = (
                int(request.form.get("controller_support"))
                if request.form.get("controller_support")
                else 0
            )

            conn.execute(
                """
                UPDATE user_game_relationship
                SET
                    catalog_status = ?,
                    date_main_completed = ?,
                    date_completed = ?,
                    hours_played = ?,
                    rating = ?,
                    user_notes = ?
                WHERE game_table_id = ?
            """,
                (
                    catalog_update,
                    date_main_update,
                    date_full_update,
                    hours_update,
                    rating_update,
                    notes_update,
                    game_table_id,
                ),
            )
            conn.commit()

            user_game_rel_id = conn.execute(
                """
                SELECT relationship_id
                FROM user_game_relationship
                WHERE game_table_id = ?
            """,
                (game_table_id,),
            ).fetchone()

            if user_game_rel_id:
                for platform in owned_platforms:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO user_platform_own (relationship_id, platform_id)
                        VALUES (?, (
                            SELECT platform_id
                            FROM game_platforms
                            WHERE platform = ?
                            AND game_table_id = ?
                        ))
                    """,
                        (user_game_rel_id[0], platform, game_table_id),
                    )
                conn.commit()

                for platform in played_platforms:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO user_played_on (relationship_id, platform_id, game_hours)
                        VALUES (?, (
                            SELECT platform_id
                            FROM game_platforms
                            WHERE platform = ?
                            AND game_table_id = ?
                        ), ?)
                    """,
                        (user_game_rel_id[0], platform, game_table_id, hours_update),
                    )
                conn.commit()
            else:
                log.warning(f"No relationship id found for game_table_id = {game_table_id}. Platforms in owned/played not updated.")

            conn.execute(
                """
                UPDATE games
                SET controller_supported = ?
                WHERE game_table_id = ?
            """,
                (controller_support, game_table_id),
            )
            conn.commit()

        except sqlite3.Error as e:
            log.error(f"There was an error when operating in the database. {type(e).__name__}: {e}")
            flash("An unexpected error occurred, try again.", "error")
            conn.rollback()
            return redirect(url_for("game_details", game_table_id=game_table_id))

        else:
            return redirect(url_for("game_details", game_table_id=game_table_id))

        finally:
            conn.close()
    else:
        return redirect(url_for("index"))