import ast
import datetime as dt
from config import get_conn
from flask import Flask, render_template, request, redirect, url_for
from gamepass import (
    get_bigIds, 
    create_master_set, 
    add_to_gamepass_table, 
    update_with_tiers,
    add_to_games_table
)
from hltb import get_hltb_info, add_hltb_info
from igdb import igdb_search, game_processing, add_game_series
from steam import (
    get_steam_info, 
    check_if_steam_game_exists, 
    steam_selection_to_query,
    write_additional_steam_game_information
)
from user_relationship import create_user_game_relationship

app = Flask(__name__)

@app.route('/')
def index():
    conn = get_conn()

    catalog_data = conn.execute("""
        SELECT
            g.game_table_id,
            g.title,
            g.release_date,
            p.title AS expansion_of,
            GROUP_CONCAT(s.series_name, ', '),
            CASE
                WHEN m.multiplayer_id is NULL then 'No'
                ELSE 'Yes'
            END AS multiplayer,
            u.catalog_status,
            u.hours_played,
            u.rating,
            u.user_notes
        FROM games g
        LEFT JOIN user_game_relationship u
        ON g.game_table_id = u.game_table_id
        LEFT JOIN multiplayer_modes m
        ON g.igdb_id = m.igdb_id
        LEFT JOIN (SELECT
            g.series_id,
            g.series_name,
            s.game_table_id
            FROM game_series g
            JOIN game_series_link s
            ON g.series_id = s.series_id
            ) s
        ON g.game_table_id = s.game_table_id                          
        LEFT JOIN games p
        ON g.expansion_of = p.game_table_id
        GROUP BY g.game_table_id, g.title, g.release_date, p.title, u.catalog_status, u.hours_played, u.rating, u.user_notes
    """).fetchall()

    conn.close()

    catalog_table = [{
        'game_table_id': game_table_id,
        'title': title, 
        'release_date': release_date,
        'expansion_of': expansion_of,
        'series_name': series_name,
        'multiplayer': multiplayer,
        'catalog_status': catalog_status,
        'hours_played': hours_played,
        'rating': rating,
        'user_notes': user_notes,
    } for game_table_id, title, release_date, expansion_of, series_name, multiplayer, catalog_status, hours_played, rating, user_notes in catalog_data]

    return render_template('index.html', catalog_table=catalog_table)

@app.route('/game_search', methods=['GET', 'POST'])
def game_search():
    if request.method == 'POST':
        game_search = request.form['game_search']
        search_results_raw = igdb_search(web_input=game_search)

        search_results = []

        for search_result in search_results_raw:
            search_results.append({
                'game_title': search_result.get('name'), 
                'release_year': dt.datetime.fromtimestamp(search_result.get('first_release_date')).year if search_result.get('first_release_date') else 'unknown', 
                'igdb_id': search_result.get('id')
            })
    
        return render_template('results.html', search_results=search_results)
    else:
        return render_template('game_search.html')
    
@app.route('/game_selection', methods=['GET', 'POST'])
def game_selection():
    if request.method == 'POST':
        game_selection = tuple(request.form['game_selection'].split(','))
        igdb_id, game_title = game_selection
        igdb_id = int(igdb_id)
        steam_game_id = int(request.form['steam_game_id']) if request.form['steam_game_id'] else None
        steam_game_playtime = float(request.form['steam_game_playtime']) if request.form['steam_game_playtime'] else None
        
        hltb_results = get_hltb_info(game_name=game_title)
        
        processed_game = game_processing(igdb_id=igdb_id)

        if steam_game_id:
            write_additional_steam_game_information(steam_game_id=steam_game_id, igdb_id=igdb_id)
        
        if isinstance(processed_game, tuple):
            game_table_id, series_ids = processed_game
            return render_template(
                'processing_series.html',
                hltb_results=hltb_results,
                game_table_id=game_table_id,
                series_ids=series_ids
            )
        else:
            return render_template(
                'processing_no_series.html',
                hltb_results=hltb_results,
                game_table_id=processed_game
            )
    else:
        return redirect(url_for('index'))
    
@app.route('/processing_series', methods=['GET', 'POST'])
def processing_series():
    if request.method == 'POST':
        series_release = int(request.form['series_release']) if request.form['series_release'] else None
        series_timeline = int(request.form['series_timeline']) if request.form['series_timeline'] else None
        series_total = int(request.form['series_total']) if request.form['series_total'] else None
        hltb_selection = tuple(request.form['hltb_selection'].split(', '))
        
        hltb_id, hltb_main_story, hltb_main_extras, hltb_completionist, hltb_all_styles = hltb_selection
        game_table_id = int(request.form['game_table_id'])
        series_ids = ast.literal_eval(request.form['series_ids'])
        
        add_hltb_info(
            hltb_id=hltb_id, 
            game_table_id=game_table_id, 
            hltb_main_story=hltb_main_story, 
            hltb_main_extras=hltb_main_extras, 
            hltb_completionist=hltb_completionist, 
            hltb_all_styles=hltb_all_styles
        )
        add_game_series(
            series_ids=series_ids, 
            row_id=game_table_id, 
            release_place=series_release, 
            timeline_place=series_timeline, 
            total_games_in_series=series_total
        )

        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))
    
@app.route('/processing_no_series', methods=['GET', 'POST'])
def processing_no_series():
    if request.method == 'POST':
        hltb_selection = tuple(request.form['hltb_selection'].split(', '))
        
        hltb_id, hltb_main_story, hltb_main_extras, hltb_completionist, hltb_all_styles = hltb_selection
        game_table_id = int(request.form['game_table_id'])
        
        add_hltb_info(
            hltb_id=hltb_id, 
            game_table_id=game_table_id, 
            hltb_main_story=hltb_main_story, 
            hltb_main_extras=hltb_main_extras, 
            hltb_completionist=hltb_completionist, 
            hltb_all_styles=hltb_all_styles
        )

        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))
    
@app.route('/steam_sync', methods=['GET', 'POST'])
def steam_sync():
    if request.method == 'POST':
        steam_games = get_steam_info()
        steam_games_not_in_db = []

        for steam_game in steam_games:
            steam_game_name = steam_game.get('name')
            steam_game_id = steam_game.get('appid')
            steam_game_playtime = round((steam_game.get('playtime_forever') / 60), 2)

            if check_if_steam_game_exists(steam_game_id):
                continue
            else:
                steam_games_not_in_db.append({
                    'steam_game_id': steam_game_id,
                    'steam_game_name': steam_game_name,
                    'steam_game_playtime': steam_game_playtime
                })
        
        return render_template('steam_review.html', steam_games_not_in_db=steam_games_not_in_db)
    else:
        return redirect(url_for('index'))
    
@app.route('/steam_search', methods = ['GET', 'POST'])
def steam_search():
    if request.method == 'POST':
        if 'steam_selection' in request.form:
            steam_selection = tuple(request.form['steam_selection'].split(', '))
            steam_game_id, steam_game_name, steam_game_playtime = steam_selection
        
            return render_template('steam_search.html', steam_selection=steam_selection, steam_game_name=steam_game_name, steam_game_id=steam_game_id)
        else:
            steam_search = request.form['steam_search']

            search_results_raw = igdb_search(web_input=steam_search)

            search_results = []

            for search_result in search_results_raw:
                name = search_result.get('name')
                release_year = dt.datetime.fromtimestamp(search_result.get('first_release_date')).year if search_result.get('first_release_date') else 'unknown'
                igdb_id = search_result.get('id')
                search_results.append({'game_title': name, 'release_year': release_year, 'igdb_id': igdb_id})
    
            return render_template('results.html', search_results=search_results)
    else:
        return redirect(url_for('index'))
    
@app.route('/gamepass_update', methods = ['GET', 'POST'])
def gamepass_update():
    if request.method == 'POST':
        conn = get_conn()

        consoles = get_bigIds()
        master_set = create_master_set(consoles)
        add_to_gamepass_table(master_set)
        update_with_tiers(consoles)
        add_to_games_table()

        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))
    
@app.route('/game_details/<int:game_table_id>')
def game_details(game_table_id):
    conn = get_conn()

    core_game_info = conn.execute("""
        SELECT 
            g.title, 
            g.release_date, 
            g.controller_supported, 
            p.title AS expansion_of
        FROM games g
        LEFT JOIN games p
        ON g.expansion_of = p.game_table_id
        WHERE g.game_table_id = ?
    """, (game_table_id, )).fetchone()

    relationship_info = conn.execute("""
        SELECT
            catalog_status,
            date_main_completed,
            date_completed,
            hours_played,
            rating,
            user_notes
        FROM user_game_relationship
        WHERE game_table_id = ?
    """, (game_table_id, )).fetchone()
    
    series_info = conn.execute("""
        SELECT 
            g.series_name,
            l.place_in_series_release,
            l.place_in_series_timeline,
            l.total_games_in_series
        FROM game_series g
        JOIN game_series_link l
        ON g.series_id = l.series_id
        WHERE l.game_table_id = ?
    """, (game_table_id, )).fetchall()

    platform_info = conn.execute("""
        SELECT p.platform
        FROM platforms p
        JOIN game_platforms g
        ON p.platform_id = g.platform_id
        WHERE g.game_table_id = ?
    """, (game_table_id, )).fetchall()

    genre_info = conn.execute("""
        SELECT g.genre
        FROM genres g
        JOIN game_genres gg
        ON g.genre_id = gg.genre_id
        WHERE gg.game_table_id = ?
    """, (game_table_id, )).fetchall()

    company_info = conn.execute("""
        SELECT
            c.company,
            g.is_publisher,
            g.is_developer
        FROM companies c
        JOIN game_involved_companies g
        ON c.company_id = g.company_id
        WHERE g.game_table_id = ?
    """, (game_table_id, )).fetchall()

    website_info = conn.execute("""
        SELECT
            w.website_type_name,
            g.website_url
        FROM website_types w
        JOIN game_websites g
        ON w.website_type_id = g.website_type_id
        WHERE g.game_table_id = ?
    """, (game_table_id, )).fetchall()

    hltb_info = conn.execute("""
        SELECT
            main_story,
            main_extras,
            completionist,
            all_play_styles
        FROM hltb_data
        WHERE game_table_id = ?
    """, (game_table_id, )).fetchone()

    age_ratings_info = conn.execute("""
        SELECT
            c.rating,
            GROUP_CONCAT(d.description, ', ') AS description
        FROM age_rating_category c
        JOIN game_ratings g
        ON c.category_id = g.category_id
        JOIN age_rating_description d
        ON d.description_id = g.description_id
        WHERE g.game_table_id = ?
        GROUP BY c.rating
    """, (game_table_id, )).fetchall()

    multiplayer_info = conn.execute("""
        SELECT
            p.platform,
            m.campaigncoop,
            m.dropin,
            m.lancoop,
            m.offlinecoop,
            m.onlinecoop,
            m.splitscreen,
            m.splitscreenonline,
            m.offlinemax,
            m.onlinemax
        FROM multiplayer_modes m
        JOIN games g
        ON m.igdb_id = g.igdb_id
        JOIN platforms p
        ON m.platform_id = p.platform_id
        WHERE g.game_table_id = ?
    """, (game_table_id, )).fetchall()

    conn.close()

    core_game_dict = {
        'game_title': core_game_info[0],
        'release_date': core_game_info[1],
        'controller_supported': core_game_info[2],
        'expansion_of': core_game_info[3]
    }

    relationship_dict = {
        'catalog_status': relationship_info[0],
        'date_main_completed': relationship_info[1],
        'date_completed': relationship_info[2],
        'hours_played': relationship_info[3],
        'rating': relationship_info[4],
        'user_notes': relationship_info[5]
    }

    series_dict = [{
        'series_name': row[0],
        'place_in_series_release': row[1],
        'place_in_series_timeline': row[2],
        'total_games_in_series': row[3]
    } for row in series_info]

    platform_dict = [{
        'platform': row[0]
    } for row in platform_info]

    genre_dict = [{
        'genre': row[0]
    } for row in genre_info]

    company_dict = [{
        'company': row[0],
        'is_publisher': row[1],
        'is_developer': row[2]
    } for row in company_info]

    website_dict = [{
        'website_type_name': row[0],
        'website_url': row[1]
    } for row in website_info]
    
    if hltb_info:
        hltb_dict = {
            'main_story': hltb_info[0],
            'main_extras': hltb_info[1],
            'completionist': hltb_info[2],
            'all_play_styles': hltb_info[3]
        }
    else:
        hltb_dict = None

    if age_ratings_info:
        age_ratings_dict = [{
            'rating': row[0],
            'description': row[1]
        } for row in age_ratings_info]
    else:
        age_ratings_dict = None

    if multiplayer_info:
        multiplayer_dict = [{
            'platform': row[0],
            'campaigncoop': row[1],
            'dropin': row[2],
            'lancoop': row[3],
            'offlinecoop': row[4],
            'onlinecoop': row[5],
            'splitscreen': row[6],
            'splitscreenonline': row[7],
            'offlinemax': row[8],
            'onlinemax': row[9]
        } for row in multiplayer_info]
    else:
        multiplayer_dict = None

    return render_template(
        'game_details.html',
        core_game_dict=core_game_dict,
        relationship_dict=relationship_dict,
        series_dict=series_dict,
        platform_dict=platform_dict,
        genre_dict=genre_dict,
        company_dict=company_dict,
        website_dict=website_dict,
        hltb_dict=hltb_dict,
        age_ratings_dict=age_ratings_dict,
        multiplayer_dict=multiplayer_dict
    )