CREATE TABLE IF NOT EXISTS games (
  game_table_id INTEGER PRIMARY KEY,
  igdb_id INT UNIQUE,
  steam_id INT UNIQUE,
  gamepass_id TEXT UNIQUE,
  title TEXT NOT NULL,
  alt_titles TEXT,
  version_title TEXT,
  version_parent TEXT,
  cover_img TEXT,
  images TEXT,
  summary TEXT,
  story TEXT,
  release_date TEXT,
  controller_supported INT,
  game_status TEXT,
  game_type TEXT,
  game_modes TEXT,
  genres TEXT,
  themes TEXT,
  age_rating_org TEXT,
  age_rating_cat TEXT,
  age_rating_synopsis TEXT,
  age_rating_desc TEXT
);

CREATE TABLE IF NOT EXISTS user_game_relationship (
  relationship_id INTEGER PRIMARY KEY,
  game_table_id INT NOT NULL,
  catalog_status TEXT NOT NULL DEFAULT 'backlog',
  date_added TEXT NOT NULL,
  date_main_completed TEXT,
  date_completed TEXT,
  hours_played REAL,
  rating REAL,
  user_notes TEXT,
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  UNIQUE (relationship_id, game_table_id)
);

CREATE TABLE IF NOT EXISTS multiplayer_modes (
  multiplayer_id INTEGER PRIMARY KEY,
  game_table_id INT NOT NULL,
  campaigncoop INT,
  dropin INT,
  lancoop INT,
  offlinecoop INT,
  onlinecoop INT,
  splitscreen INT,
  splitscreenonline INT,
  offlinemax INT,
  onlinemax INT,
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  UNIQUE (multiplayer_id, game_table_id)
);

CREATE TABLE IF NOT EXISTS external_sources (
  ext_src_id INTEGER PRIMARY KEY,
  game_table_id INT NOT NULL,
  ext_src TEXT NOT NULL,
  ext_src_uid TEXT NOT NULL UNIQUE,
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  UNIQUE (ext_src_id, game_table_id)
);

CREATE TABLE IF NOT EXISTS game_involved_companies (
  company_id INTEGER PRIMARY KEY,
  game_table_id INT NOT NULL,
  company TEXT NOT NULL,
  is_developer INT NOT NULL,
  is_porting INT NOT NULL,
  is_publisher INT NOT NULL,
  is_supporting INT NOT NULL,
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  UNIQUE (game_table_id, company)
);

CREATE TABLE IF NOT EXISTS game_platforms (
  platform_id INTEGER PRIMARY KEY,
  game_table_id INT NOT NULL,
  platform TEXT NOT NULL,
  platform_abbr TEXT,
  alt_platform_name TEXT,
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  UNIQUE (game_table_id, platform)
);

CREATE TABLE IF NOT EXISTS game_websites (
  website_id INTEGER PRIMARY KEY,
  game_table_id INT NOT NULL,
  website_type TEXT NOT NULL,
  website_url TEXT NOT NULL unique,
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  UNIQUE (game_table_id, website_type)
);

CREATE TABLE IF NOT EXISTS game_series (
  series_id INTEGER PRIMARY KEY,
  game_table_id INT NOT NULL,
  series TEXT NOT NULL,
  total_games_in_series INT,
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  UNIQUE (game_table_id, series)
);

CREATE TABLE IF NOT EXISTS additional_game_content (
  content_id INTEGER PRIMARY KEY,
  game_table_id INT NOT NULL,
  parent_game TEXT,
  remakes TEXT,
  remasters TEXT,
  dl_content TEXT,
  expansions TEXT,
  expanded_games TEXT,
  standalone_expansions TEXT,
  series_forks TEXT,
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id)
);

CREATE TABLE IF NOT EXISTS hltb_data (
  hltb_id INTEGER PRIMARY KEY AUTOINCREMENT,
  game_table_id INT NOT NULL,
  main_story REAL,
  main_extras REAL,
  completionist REAL,
  all_play_styles REAL,
  FOREIGN KEY (game_table_id) REFERENCES games(game_table_id),
  UNIQUE (hltb_id, game_table_id)
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

CREATE TABLE IF NOT EXISTS user_platform_own (
  relationship_id INT NOT NULL,
  platform_id INT NOT NULL,
  PRIMARY KEY (relationship_id, platform_id),
  FOREIGN KEY (relationship_id) REFERENCES user_game_relationship(relationship_id),
  FOREIGN KEY (platform_id) REFERENCES game_platforms(platform_id)
);

CREATE TABLE IF NOT EXISTS user_played_on (
  relationship_id INT NOT NULL,
  platform_id INT NOT NULL,
  game_hours REAL,
  PRIMARY KEY (relationship_id, platform_id),
  FOREIGN KEY (relationship_id) REFERENCES user_game_relationship(relationship_id),
  FOREIGN KEY (platform_id) REFERENCES game_platforms(platform_id)
);