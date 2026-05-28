import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()
CLIENT_ID = os.getenv('client_id')
CLIENT_SECRET = os.getenv('client_secret')
GRANT_TYPE = os.getenv('grant_type')

DB_PATH = 'games.db'
ESRB_RATING_ID = 1
AGE_DESCRIPTION_TYPE = 1

IGDB_GAMES_ENDPOINT = 'https://api.igdb.com/v4/games'
IGDB_MULTIPLAYER_ENDPOINT = 'https://api.igdb.com/v4/multiplayer_modes'
IGDB_GENRE_ENDPOINT = 'https://api.igdb.com/v4/genres'
IGDB_PLATFORMS_ENDPOINT = 'https://api.igdb.com/v4/platforms'
IGDB_COMPANIES_ENDPOINT = 'https://api.igdb.com/v4/companies'
IGDB_INVOLVED_COMPANIES_ENDPOINT = 'https://api.igdb.com/v4/involved_companies'
IGDB_COLLECTIONS_ENDPOINT = 'https://api.igdb.com/v4/collections'
IGDB_MULTIPLAYER_ENDPOINT = 'https://api.igdb.com/v4/multiplayer_modes'
IGDB_WEBSITE_TYPES_ENDPOINT = 'https://api.igdb.com/v4/website_types'
IGDB_WEBSITE_ENDPOINT = 'https://api.igdb.com/v4/websites'
IGDB_AGE_RATINGS_ENDPOINT = 'https://api.igdb.com/v4/age_ratings'
IGDB_AGE_CATEGORIES_ENDPOINT = 'https://api.igdb.com/v4/age_rating_categories'
IGDB_AGE_DESCRIPTION_ENDPOINT = 'https://api.igdb.com/v4/age_rating_content_descriptions_v2'

STEAM_ENDPOINT = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/'

REFERENCE_TABLES = {
  'genres': {
    'endpoint': IGDB_GENRE_ENDPOINT,
    'fields': ['name'],
    'table': 'genres',
    'columns': ['genre_id', 'genre']
  },
  'platforms': {
    'endpoint': IGDB_PLATFORMS_ENDPOINT,
    'fields': ['name'],
    'table': 'platforms',
    'columns': ['platform_id', 'platform']
  },
  'website_types': {
    'endpoint': IGDB_WEBSITE_TYPES_ENDPOINT,
    'fields': ['type'],
    'table': 'website_types',
    'columns': ['website_type_id', 'website_type_name']
  },
  'age_rating_category': {
    'endpoint': IGDB_AGE_CATEGORIES_ENDPOINT,
    'fields': ['rating'],
    'table': 'age_rating_category',
    'columns': ['category_id', 'rating']
  },
  'age_rating_description': {
    'endpoint': IGDB_AGE_DESCRIPTION_ENDPOINT,
    'fields': ['description'],
    'table': 'age_rating_description',
    'columns': ['description_id', 'description']
  }
}

def get_conn ():
  conn = sqlite3.connect(DB_PATH)
  conn.execute("PRAGMA foreign_keys = ON")
  return conn

# GAMEPASS
catalog_of_ids_url = 'https://catalog.gamepass.com/sigls/v3?'
catalog_of_titles_url = 'https://displaycatalog.mp.microsoft.com/v7.0/products?'

GAMEPASS_PLATFORMS = [
  'ConsoleGen8',
  'ConsoleGen9',
  'ConsoleGen8;ConsoleGen9',
  'pc'
]

GAMEPASS_TIERS = {
  'ultimate': {
    'tier_code': 'CFQ7TTC0KHS0',
    'sigl': '97c6c862-d28a-4907-a3d5-c401f2296a53'
  },
  'premium': {
    'tier_code': 'CFQ7TTC0P85B',
    'sigl': '09a72c0d-c466-426a-9580-b78955d8173a'
  },
  'essential': {
    'tier_code': 'CFQ7TTC0K5DJ',
    'sigl': '34031711-5a70-4196-bab7-45757dc2294e'
  },
  'console': {
    'tier_code': 'CFQ7TTC0K6L8',
    'sigl': 'f6f1f99f-9b49-4ccd-b3bf-4d9767a77f5e'
  },
  'pc': {
    'tier_code': 'CFQ7TTC0KGQ8',
    'sigl': '609d944c-d395-4c0a-9ea4-e9f39b52c1ad'
  }
}

#'recently_added': '06323672-b8c8-43cc-b0de-32d5a9834749'
#'most_popular_a': 'eab7757c-ff70-45af-bfa6-79d3cfb2bf81'
#'coming_to_gamepass_a': '095bda36-f5cd-43f2-9ee1-0a72f371fb96'
#'leaving_soon_a': '393f05bf-e596-4ef6-9487-6d4fa0eab987'
#'most_popular_b': 'a884932a-f02b-40c8-a903-a008c23b1df1'
#'coming_to_gamepass_b': '4165f752-d702-49c8-886b-fb57936f6bae'
#'leaving_soon_b': 'cc7fc951-d00f-410e-9e02-5e4628e04163
# GAMEPASS_EA_PLAY = 'CFQ7TTC0K5DH'
# GAMEPASS_UBISOFT = 'CFQ7TTC0QH5H'