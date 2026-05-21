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