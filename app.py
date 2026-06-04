import datetime as dt
from config import get_conn
from flask import Flask, render_template, request, redirect, url_for
from gamepass import get_bigIds, create_master_set, add_to_gamepass_table, update_with_tiers
from hltb import get_hltb_info, add_hltb_info
from igdb import igdb_search, game_processing, add_game_series
from steam import (
    get_steam_info, 
    check_if_steam_game_exists, 
    steam_selection_to_query,
    write_additional_steam_game_information
)

app = Flask(__name__)

@app.route('/')
def index():
    conn = get_conn()

    catalog_data = conn.execute("""
        SELECT 
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
        GROUP BY g.title, g.release_date, p.title, u.catalog_status, u.hours_played, u.rating, u.user_notes
    """).fetchall()

    conn.close()

    catalog_table = [{
        'title': title, 
        'release_date': release_date,
        'expansion_of': expansion_of,
        'series_name': series_name,
        'multiplayer': multiplayer,
        'catalog_status': catalog_status,
        'hours_played': hours_played,
        'rating': rating,
        'user_notes': user_notes,
    } for title, release_date, expansion_of, series_name, multiplayer, catalog_status, hours_played, rating, user_notes in catalog_data]

    return render_template('index.html', catalog_table = catalog_table)

@app.route('/game_search', methods = ['GET', 'POST'])
def game_search():
    if request.method == 'POST':
        game_search = request.form['game_search']
        search_results_raw = igdb_search(web_input = game_search)

        search_results = []

        for search_result in search_results_raw:
            name = search_result.get('name')
            release_year = dt.datetime.fromtimestamp(search_result.get('first_release_date')).year if search_result.get('first_release_date') else 'unknown'
            igdb_id = search_result.get('id')
            search_results.append({'game_title': name, 'release_year': release_year, 'igdb_id': igdb_id})
    
        return render_template('results.html', search_results = search_results)
    else:
        return render_template('game_search.html')
    
@app.route('/game_selection', methods = ['GET', 'POST'])
def game_selection():
    if request.method == 'POST':
        game_selection = tuple(request.form['game_selection'].split(','))
        igdb_id, game_title = game_selection
        igdb_id = int(igdb_id)
        steam_game_id = request.form['steam_game_id']
        
        hltb_results = get_hltb_info(game_title)
        processed_game = game_processing(igdb_id)
        write_additional_steam_game_information(steam_game_id, igdb_id)
        
        if isinstance(processed_game, tuple):
            game_table_id, series_ids = processed_game
            return render_template(
                'processing_series.html',
                hltb_results = hltb_results,
                game_table_id = game_table_id,
                series_ids = series_ids
            )
        else:
            return render_template(
                'processing_no_series.html',
                hltb_results = hltb_results,
                game_table_id = processed_game
            )
    else:
        return redirect(url_for('index'))
    
@app.route('/processing_series', methods = ['GET', 'POST'])
def processing_series():
    if request.method == 'POST':
        series_release = request.form['series_release']
        series_timeline = request.form['series_timeline']
        series_total = request.form['series_total']
        hltb_selection = tuple(request.form['hltb_selection'].split(', '))

        hltb_id, hltb_main_story, hltb_main_extras, hltb_completionist, hltb_all_styles = hltb_selection
        game_table_id = request.form['game_table_id']
        series_ids = request.form['series_ids']
        print(series_release, series_timeline, series_total, hltb_id, hltb_main_story, game_table_id, series_ids)
        add_hltb_info(hltb_id, game_table_id, hltb_main_story, hltb_main_extras, hltb_completionist, hltb_all_styles)
        add_game_series(series_ids, game_table_id, series_release, series_timeline, series_total)

        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))
    
@app.route('/processing_no_series', methods = ['GET', 'POST'])
def processing_no_series():
    if request.method == 'POST':
        hltb_selection = tuple(request.form['hltb_selection'].split(', '))

        hltb_id, hltb_main_story, hltb_main_extras, hltb_completionist, hltb_all_styles = hltb_selection
        game_table_id = request.form['game_table_id']
        
        add_hltb_info(hltb_id, game_table_id, hltb_main_story, hltb_main_extras, hltb_completionist, hltb_all_styles)

        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))
    
@app.route('/steam_sync', methods = ['GET', 'POST'])
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
        
        return render_template('steam_review.html', steam_games_not_in_db = steam_games_not_in_db)
    else:
        return redirect(url_for('index'))
    
@app.route('/steam_search', methods = ['GET', 'POST'])
def steam_search():
    if request.method == 'POST':
        if 'steam_selection' in request.form:
            steam_selection = tuple(request.form['steam_selection'].split(', '))
            steam_game_id, steam_game_name, steam_game_playtime = steam_selection
        
            return render_template('steam_search.html', steam_selection = steam_selection, steam_game_name = steam_game_name, steam_game_id = steam_game_id)
        else:
            steam_search = request.form['steam_search']
            steam_game_id = request.form['steam_game_id']

            search_results_raw = igdb_search(web_input = steam_search)

            search_results = []

            for search_result in search_results_raw:
                name = search_result.get('name')
                release_year = dt.datetime.fromtimestamp(search_result.get('first_release_date')).year if search_result.get('first_release_date') else 'unknown'
                igdb_id = search_result.get('id')
                search_results.append({'game_title': name, 'release_year': release_year, 'igdb_id': igdb_id})
    
            return render_template('results.html', search_results = search_results, steam_game_id = steam_game_id)
    else:
        return redirect(url_for('index'))
    
@app.route('/gamepass_update', methods = ['GET', 'POST'])
def gamepass_update():
    if request.method == 'POST':
        consoles = get_bigIds()
        master_set = create_master_set(consoles)
        add_to_gamepass_table(master_set)
        update_with_tiers(consoles)

        return redirect(url_for('index'))
    else:
        return redirect(url_for('index'))