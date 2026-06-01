import datetime as dt
from config import get_conn
from igdb import igdb_search, user_selection_to_query

search_results_raw = igdb_search(web_input = 'Tomb Raider')

search_results = []

for search_result in search_results_raw:
    name = search_result.get('name')
    release_year = dt.datetime.fromtimestamp(search_result.get('first_release_date')).year if search_result.get('first_release_date') else 'unknown'
    search_results.append({'game_title': name, 'release_year': release_year})

print(search_results)