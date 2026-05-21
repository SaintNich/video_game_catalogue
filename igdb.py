import datetime as dt
import requests
from access_token import create_header
from config import (
  IGDB_GAMES_ENDPOINT,
  IGDB_COMPANIES_ENDPOINT,
  IGDB_INVOLVED_COMPANIES_ENDPOINT,
  IGDB_COLLECTIONS_ENDPOINT,
  IGDB_MULTIPLAYER_ENDPOINT,
  IGDB_WEBSITE_ENDPOINT,
  IGDB_AGE_RATINGS_ENDPOINT,
  ESRB_RATING_ID,
  get_conn
)

header = create_header()

def igdb_search(igdb_id: int = None) -> list:
  if igdb_id is None:
    title_search = input("What game are you looking for? ")
  
    # string for "APIcalypse" format, limited to 20
    body = f"fields name, first_release_date; search \"{title_search}\"; limit 20;"
    search_results = requests.post(IGDB_GAMES_ENDPOINT, headers = header, data = body).json()

  else:
    body = f"fields name, first_release_date; where id = {igdb_id}; sort id asc;"
    search_results = requests.post(IGDB_GAMES_ENDPOINT, headers = header, data = body).json()
  
  return search_results
 
def user_selection_to_query(search_results) -> int:
  # creates the list for the user to view of options
  for i, result in enumerate(search_results):
    game_title = result.get('name')
    release_year = dt.datetime.fromtimestamp(result.get('first_release_date')).year if result.get('first_release_date') else 'unknown'
    igdb_id = result.get('id')
    print(f"{i+1}. {game_title}, released in {release_year} [ID = {igdb_id}]")

  try:
    while True:
      selection = input("Choose the correct entry: ")
      
      if 1 <= int(selection) <= len(search_results):
        break
      print("Be sure to choose a number in the list")
   
    # choice needs to be from index 0
    choice = search_results[int(selection) - 1]
    igdb_id = choice.get('id')
    
    return igdb_id

  except ValueError:
    print("Please enter an integer")
    return user_selection_to_query(search_results)

def full_game_info(igdb_id: int, search_results = None):
  if search_results is None:  
    srch_results = igdb_search(igdb_id)
    srch_result = srch_results[0]
    igdb_id = srch_result.get('id')
  
  else:
    game_title = search_results.get('name')
    release_year = dt.datetime.fromtimestamp(search_results.get('first_release_date')).year if search_results.get('first_release_date') else 'unknown'
    while True:
      # allow "yes", "no", "y", or "n" regardless of case
      confirm_choice = input(f"You selected {game_title}, released in {release_year}, correct? (\"Yes\" or \"No\"): ").lower()
      if confirm_choice == 'yes' or confirm_choice == 'y' or confirm_choice == 'no' or confirm_choice == 'n':
        break
      print("Please enter \"Yes\" or \"No\"")
  
  if search_results is None or confirm_choice == 'yes' or confirm_choice == 'y':
    body = f"fields name, first_release_date, genres, platforms, involved_companies, collections, multiplayer_modes, parent_game, expansions, websites, age_ratings; where id = {igdb_id}; sort id asc;"
    full_game_results = requests.post(IGDB_GAMES_ENDPOINT, headers = header, data = body).json()
  else:
    # if user says the selection was wrong, starts back at selection
    return user_selection_to_query(search_results)

  # remove the confirmed result from the list
  full_game_result = full_game_results[0]
  
  return full_game_result 
  
def game_import_to_sqlite(full_game_result):
  conn = get_conn()

  try:
    parent_id = full_game_result.get('parent_game')

    if parent_id:
      parent_row = conn.execute("""
        SELECT game_table_id FROM games WHERE igdb_id = ?
      """, (parent_id,)).fetchone()
      expansion_of = parent_row[0] if parent_row else None
    else:
      expansion_of = None

    conn.execute("""
      INSERT OR IGNORE INTO games (igdb_id, title, release_date, expansion_of)
      VALUES (?, ?, ?, ?)
    """, (
      full_game_result.get('id'),
      full_game_result.get('name'),
      dt.datetime.fromtimestamp(full_game_result.get('first_release_date')).date().isoformat() if full_game_result.get('first_release_date') else 'unknown',
      expansion_of
    ))

    row_ids = conn.execute("""
    SELECT game_table_id
    FROM games
    WHERE igdb_id = ?
    """, (full_game_result.get('id'),)).fetchone()

    conn.commit()

    # remove the list from the row_id
    row_id = row_ids[0]

    return row_id

  finally:
    conn.close()

def add_game_genre_platform(row_id, tbl_ids, tables, columns):
  conn = get_conn()
  
  try:
    for ids, column, table in zip(tbl_ids, columns, tables):
      for id in ids:
        conn.execute(f"""
          INSERT OR IGNORE INTO {table} (game_table_id, {column})
          VALUES (?, ?)
        """, (row_id, id))

    conn.commit()
  
  finally:
    conn.close()

def add_game_companies(row_id, inv_comp_ids):
  conn = get_conn()

  for inv_comp_id in inv_comp_ids:
    first_body = f"fields company, developer, publisher; where id = {inv_comp_id}; sort id asc;"
    inv_comp_results = requests.post(IGDB_INVOLVED_COMPANIES_ENDPOINT, headers = header, data = first_body).json()
    inv_comp_result = inv_comp_results[0]
    company = inv_comp_result.get('company')
    developer = int(inv_comp_result.get('developer', False))
    publisher = int(inv_comp_result.get('publisher', False))
    
    second_body = f"fields name; where id = {company}; sort id asc;"
    comp_results = requests.post(IGDB_COMPANIES_ENDPOINT, headers = header, data = second_body).json()
    comp_result = comp_results[0]
    
    conn.execute("""
      INSERT OR IGNORE INTO companies (company_id, company)
      VALUES (?, ?)             
    """, (
        comp_result.get('id'),
        comp_result.get('name')
    ))

    conn.execute("""
      INSERT OR IGNORE INTO game_involved_companies (game_table_id, company_id, is_developer, is_publisher)
      VALUES (?, ?, ?, ?)
    """, (
      row_id,
      comp_result.get('id'),
      developer,
      publisher
    ))
    
  conn.commit()
  conn.close()
      
def add_game_series(series_ids):
  conn = get_conn()

  if series_ids is None:
    return

  for series_id in series_ids:
    body = f"fields name, games; where id = {series_id}; sort id asc;"
    series_results = requests.post(IGDB_COLLECTIONS_ENDPOINT, headers = header, data = body).json()
    series_result = series_results[0]

    conn.execute("""
      INSERT OR IGNORE INTO game_series (series_id, series_name, total_games_in_series)
      VALUES (?, ?, ?)
    """, (
      series_result.get('id'),
      series_result.get('name'),
      len(series_result.get('games') or [])
    ))

  conn.commit()
  conn.close()

def add_multiplayer_modes(multi_ids):
  conn = get_conn()

  for multi_id in multi_ids:
    body = f"fields game, platform, campaigncoop, dropin, lancoop, offlinecoop, onlinecoop, splitscreen, splitscreenonline, offlinemax, onlinemax; where id = {multi_id}; sort id asc;"
    multiplayer_results = requests.post(IGDB_MULTIPLAYER_ENDPOINT, headers = header, data = body).json()
    multiplayer_result = multiplayer_results[0]
 
    conn.execute("""
      INSERT OR IGNORE INTO multiplayer_modes (
        multiplayer_id,
        igdb_id,
        platform_id,
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
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
      multiplayer_result.get('id'),
      multiplayer_result.get('game'),
      multiplayer_result.get('platform'),
      int(multiplayer_result.get('campaigncoop')) if multiplayer_result.get('campaigncoop') else None,
      int(multiplayer_result.get('dropin')) if multiplayer_result.get('dropin') else None,
      int(multiplayer_result.get('lancoop')) if multiplayer_result.get('lancoop') else None,
      int(multiplayer_result.get('offlinecoop')) if multiplayer_result.get('offlinecoop') else None,
      int(multiplayer_result.get('onlinecoop')) if multiplayer_result.get('onlinecoop') else None,
      int(multiplayer_result.get('splitscreen')) if multiplayer_result.get('splitscreen') else None,
      int(multiplayer_result.get('splitscreenonline')) if multiplayer_result.get('splitscreenonline') else None,
      multiplayer_result.get('offlinemax'),
      multiplayer_result.get('onlinemax')
    ))

  conn.commit()
  conn.close()

def add_game_websites(websites, row_id):
  conn = get_conn()
  
  for website in websites:
    body = f"fields game, type, url; where id = {website}; sort id asc;"
    site_results = requests.post(IGDB_WEBSITE_ENDPOINT, headers = header, data = body).json()
    site_result = site_results[0]

    conn.execute("""
      INSERT OR IGNORE INTO game_websites (
        game_table_id,
        website_id,
        website_type_id,
        website_url
      )
      VALUES (?, ?, ?, ?)
    """, (
      row_id,
      site_result.get('id'),
      site_result.get('type'),
      site_result.get('url')
    ))

  conn.commit()
  conn.close()

def add_age_ratings(age_ratings, row_id):
  conn = get_conn()

  for rating in age_ratings:
    body = f"fields rating_category, rating_content_descriptions; where organization = {ESRB_RATING_ID} & id = {rating}; sort id asc;"
    rating_results = requests.post(IGDB_AGE_RATINGS_ENDPOINT, headers = header, data = body).json()

    if not rating_results:
      continue

    rating_result = rating_results[0]

    description_ids = rating_result.get('rating_content_descriptions') or []
    
    for description_id in description_ids:
      conn.execute("""
        INSERT OR IGNORE INTO game_ratings (game_table_id, age_rating_id, category_id, description_id)
        VALUES (?, ?, ?, ?)
      """, (
        row_id,
        rating_result.get('id'),
        rating_result.get('rating_category'),
        description_id
      ))
    
  conn.commit()
  conn.close()

def add_game_expansions(expansions):
  for expansion in expansions:
    game_processing(expansion)

def game_processing(igdb_id): 
  tables = ['game_genres', 'game_platforms']
  columns = ['genre_id', 'platform_id']
  
  full_game_result = full_game_info(igdb_id)
  igdb_id = full_game_result.get('id')
  row_id = game_import_to_sqlite(full_game_result)
  tbl_ids = [full_game_result.get('genres'), full_game_result.get('platforms')]
  add_game_genre_platform(row_id, tbl_ids, tables, columns)
  
  inv_comp_ids = full_game_result.get('involved_companies')
  add_game_companies(row_id, inv_comp_ids)
  
  series_ids = full_game_result.get('collections')
  add_game_series(series_ids)
  
  websites = full_game_result.get('websites')
  add_game_websites(websites, row_id)
  
  age_ratings = full_game_result.get('age_ratings')
  if age_ratings:
    add_age_ratings(age_ratings, row_id)

  multi_ids = full_game_result.get('multiplayer_modes')
  if multi_ids:
    add_multiplayer_modes(multi_ids)

  expansions = full_game_result.get('expansions')
  if expansions:
    add_game_expansions(expansions)

  return igdb_id
  
def main():
  search_results = igdb_search()
  igdb_id = user_selection_to_query(search_results)

  game_processing(igdb_id)

if __name__ == "__main__":
  main()