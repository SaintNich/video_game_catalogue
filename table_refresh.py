import datetime as dt
import requests
from access_token import create_header
from config import ESRB_RATING_ID, AGE_DESCRIPTION_TYPE, REFERENCE_TABLES, get_conn

query_table = ['genres', 'platforms', 'website_types', 'age_rating_category', 'age_rating_description']

def get_table(query_table):
  cfg = REFERENCE_TABLES[query_table]
  cfg_endpoint = cfg['endpoint']
  cfg_fields = cfg['fields']

  if query_table == 'age_rating_category':
    body = f"fields {', '.join(cfg_fields)}; where organization = {ESRB_RATING_ID}; limit 500;"
  elif query_table == 'age_rating_description':
    body = f"fields {', '.join(cfg_fields)}; where organization = {ESRB_RATING_ID} & description_type = {AGE_DESCRIPTION_TYPE}; limit 500;"
  else:
    body = f"fields {', '.join(cfg_fields)}; limit 500;"

  results = requests.post(cfg_endpoint, headers = create_header(), data = body).json()

  return results

def add_or_update_table(query_table, results):
  today = dt.datetime.today().date().isoformat()
  cfg = REFERENCE_TABLES[query_table]
  cfg_table = cfg['table']
  cfg_columns = cfg['columns']
  conn = get_conn()

  try:
    for result in results:
      if cfg_table == 'website_types':
        field = result.get('type')
      elif cfg_table == 'age_rating_category':
        field = result.get('rating')
      elif cfg_table == 'age_rating_description':
        field = result.get('description')
      else:
        field = result.get('name')
      
      conn.execute(f"""
        INSERT OR REPLACE INTO {cfg_table} ({', '.join(cfg_columns)})
        VALUES (?, ?)
      """, (
        result.get('id'),
        field
      ))

    conn.execute("""
      INSERT OR REPLACE INTO igdb_table_refresh (table_name, last_updated)
      VALUES (?, ?)
    """, (cfg_table, today))
    
    conn.commit()
  
  finally:
    conn.close()

def main():
  for table in query_table:
    results = get_table(table)
    add_or_update_table(table, results)

if __name__ == "__main__":
  main()