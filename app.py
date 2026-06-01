import datetime as dt
from config import get_conn
from igdb import igdb_search, game_processing, add_game_series
from hltb import get_hltb_info, add_hltb_info
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    conn = get_conn()

    relationship_data = conn.execute("""
        SELECT 
            g.title,
            g.release_date,
            u.catalog_status,
            u.rating,
            u.user_notes
        FROM games g
        JOIN user_game_relationship u
        ON g.game_table_id = u.game_table_id
    """).fetchall()

    conn.close()

    relationship_table = [{
        'title': title, 
        'release_date': release_date,
        'catalog_status': catalog_status,
        'rating': rating,
        'user_notes': user_notes
    } for title, release_date, catalog_status, rating, user_notes in relationship_data]

    return render_template('index.html')

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
        
        hltb_results = get_hltb_info(game_title)
        processed_game = game_processing(igdb_id)
        
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