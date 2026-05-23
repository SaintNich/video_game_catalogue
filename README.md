# Game Library Manager

A personal game cataloguing system built to address shortcomings found in existing solutions. Existing solutions like GoodReads-style game trackers and spreadsheets either lack cross-platform ownership tracking, don’t distinguish between owning and playing, or can’t handle subscription services like Game Pass cleanly. This project solves all three. 

Allows full game entry and tracking across multiple platforms using IGDB as the primary metadata source.

## Current Features
- Manual game entry via IGDB search and confirmation
- Full metadata pull including genres, platforms, companies, series, multiplayer modes, websites, and ESRB ratings
- Expansion tracking with automatic addition of related titles
- Steam library synchronization with playtime tracking
- Reference table sync for genres, platforms, and website types

## Design Philosophy
Most existing game tracking solutions treat library management as a flat list. This project models it relationally — separating catalogue data (games that exist) from library data (games I have a personal relationship with). A game enters the catalogue when it’s imported from IGDB. A user_game_relationship record is only created when ownership or playtime is explicitly recorded — meaning Game Pass titles sit in the catalogue without inflating the library until actually played.

The schema uses junction tables for genres, platforms, companies, and multiplayer modes, keeping metadata normalized and queryable rather than stored as flat strings.

## What I Built and Why
- Modeled catalogue vs. library as distinct concepts rather than a single list
- Designed `user_game_relationship` as a triggered record rather than automatic — ownership or playtime creates it, not import
- Used junction tables for all many-to-many relationships to keep data queryable
- Chose SQLite for portability — the entire library lives in a single file

## Setup

### Requirements
- Python 3.x
- SQLite3

### Installation
1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Create a `.env` file in the project root with the following:
    - IGDB_CLIENT_ID=your_client_id
    - IGDB_CLIENT_SECRET=your_client_secret
    - IGDB_GRANT_TYPE=client_credentials
    - STEAM_API_KEY=your_steam_api_key
    - STEAM_ID=your_steam_id

5. Initialize the database by running `schema.sql`

## Usage

**Add a game manually:**
python igdb.py

**Sync Steam library:**
python steam.py

**Refresh reference tables:**
python table_refresh.py

## Known Limitations
- Steam games must be manually matched to their IGDB entry on first sync
- Epic Games, GOG, Ubisoft Connect, and Amazon Games require manual entry — no public API available
- IGDB data quality varies, particularly for older titles and multiplayer mode coverage

## Planned Enhancements
- HowLongToBeat integration for completion time estimates
- Xbox Game Pass catalog scraping
- Refactor API calls to utilize IGDB expander feature for reduced request overhead
- UI layer for library browsing and management
- User relationship tracking (ownership, play status, ratings)