CREATE TABLE IF NOT EXISTS games (
  game_table_id INTEGER PRIMARY KEY AUTOINCREMENT,
  igdb_id INT UNIQUE,
  steam_id INT UNIQUE,
  gamepass_id TEXT UNIQUE,
  title TEXT NOT NULL,
  release_date TEXT,
  controller_supported INT,
  expansion_of INT,
  FOREIGN KEY (expansion_of) REFERENCES games(game_table_id)
);

CREATE TABLE IF NOT EXISTS game_series (
  series_id INT PRIMARY KEY,
  series_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_game_relationship (
  relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_table_id INT NOT NULL,
  catalog_status TEXT NOT NULL DEFAULT 'Backlog',
  date_added TEXT NOT NULL,
  date_main_completed TEXT,
  date_completed TEXT,
  hours_played REAL,
  rating REAL,
  user_notes TEXT,
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id)
);

CREATE TABLE IF NOT EXISTS platforms (
  platform_id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS genres (
  genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
  genre TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS companies (
  company_id INTEGER PRIMARY KEY AUTOINCREMENT,
  company TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS multiplayer_modes (
  multiplayer_id INTEGER PRIMARY KEY AUTOINCREMENT,
  igdb_id INT NOT NULL,
  platform_id INT NOT NULL,
  campaigncoop INT,
  dropin INT,
  lancoop INT,
  offlinecoop INT,
  onlinecoop INT,
  splitscreen INT,
  splitscreenonline INT,
  offlinemax INT,
  onlinemax INT,
  FOREIGN KEY (igdb_id) REFERENCES games(igdb_id),
  FOREIGN KEY (platform_id) REFERENCES platforms(platform_id)
);

CREATE TABLE IF NOT EXISTS website_types (
  website_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
  website_type_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS age_rating_category (
  category_id INTEGER PRIMARY KEY AUTOINCREMENT,
  rating TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS age_rating_description (
  description_id INTEGER PRIMARY KEY AUTOINCREMENT,
  description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hltb_data (
  hltb_id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_table_id INT NOT NULL,
  main_story REAL,
  main_extras REAL,
  completionist REAL,
  all_play_styles REAL,
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id)
);

CREATE TABLE IF NOT EXISTS gamepass_catalog (
  gamepass_id TEXT PRIMARY KEY,
  game_title TEXT NOT NULL,
  active_on_gamepass INT DEFAULT 0,
  ultimate INT DEFAULT 0,
  premium INT DEFAULT 0,
  essential INT DEFAULT 0,
  console INT DEFAULT 0,
  pc INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS game_genres (
  game_table_id INT NOT NULL,
  genre_id INT NOT NULL,
  PRIMARY KEY (game_table_id, genre_id),
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  FOREIGN KEY (genre_id) REFERENCES genres(genre_id)
);

CREATE TABLE IF NOT EXISTS game_platforms (
  game_table_id INT NOT NULL,
  platform_id INT NOT NULL,
  PRIMARY KEY (game_table_id, platform_id),
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  FOREIGN KEY (platform_id) REFERENCES platforms(platform_id)
);

CREATE TABLE IF NOT EXISTS game_involved_companies (
  game_table_id INT NOT NULL,
  company_id INT NOT NULL,
  is_developer INT NOT NULL,
  is_publisher INT NOT NULL,
  PRIMARY KEY (game_table_id, company_id),
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE IF NOT EXISTS game_websites (
  game_table_id INT NOT NULL,
  website_id INT NOT NULL,
  website_type_id INT NOT NULL,
  website_url TEXT NOT NULL,
  PRIMARY KEY (game_table_id, website_id),
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  FOREIGN KEY (website_type_id) REFERENCES website_types(website_type_id)
);

CREATE TABLE IF NOT EXISTS game_ratings (
  game_table_id INT NOT NULL,
  age_rating_id INT NOT NULL,
  category_id INT NOT NULL,
  description_id INT NOT NULL,
  PRIMARY KEY (game_table_id, age_rating_id, category_id, description_id),
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  FOREIGN KEY (category_id) REFERENCES age_rating_category(category_id),
  FOREIGN KEY (description_id) REFERENCES age_rating_description(description_id)
);

CREATE TABLE IF NOT EXISTS game_series_link (
  game_table_id INT NOT NULL,
  series_id INT NOT NULL,
  place_in_series_release INT,
  place_in_series_timeline INT,
  total_games_in_series INT,
  PRIMARY KEY (game_table_id, series_id),
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  FOREIGN KEY (series_id) REFERENCES game_series(series_id)
);

CREATE TABLE IF NOT EXISTS user_platform_own (
  relationship_id INT NOT NULL,
  platform_id INT NOT NULL,
  PRIMARY KEY (relationship_id, platform_id),
  FOREIGN KEY (relationship_id) REFERENCES user_game_relationship(relationship_id),
  FOREIGN KEY (platform_id) REFERENCES platforms(platform_id)
);

CREATE TABLE IF NOT EXISTS user_played_on (
  relationship_id INT NOT NULL,
  platform_id INT NOT NULL,
  game_hours REAL,
  PRIMARY KEY (relationship_id, platform_id),
  FOREIGN KEY (relationship_id) REFERENCES user_game_relationship(relationship_id),
  FOREIGN KEY (platform_id) REFERENCES platforms(platform_id)
);

CREATE TABLE IF NOT EXISTS igdb_table_refresh (
  table_name TEXT PRIMARY KEY,
  last_updated TEXT
);

/*
WITH comb_genres AS (
  SELECT
    game_genres.game_table_id,
    GROUP_CONCAT(genres.genre, ', ') AS genre
  FROM game_genres
  JOIN genres
  ON game_genres.genre_id = genres.genre_id
  GROUP BY game_genres.game_table_id
), 
comb_platforms AS (
  SELECT
    game_platforms.game_table_id,
    GROUP_CONCAT(platforms.platform, ', ') AS platform
  FROM game_platforms
  JOIN platforms
  ON game_platforms.platform_id = platforms.platform_id
  GROUP BY game_platforms.game_table_id
)
SELECT
  games.game_table_id,
  games.igdb_id,
  games.title,
  comb_genres.genre,
  comb_platforms.platform
FROM games
LEFT JOIN comb_genres
ON games.game_table_id = comb_genres.game_table_id
LEFT JOIN comb_platforms
ON games.game_table_id = comb_platforms.game_table_id;
*/