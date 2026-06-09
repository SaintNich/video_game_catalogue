import datetime as dt
import requests
from config import GAMEPASS_TIERS, GAMEPASS_PLATFORMS, catalog_of_ids_url, catalog_of_titles_url, get_conn
from igdb import header, IGDB_GAMES_ENDPOINT, game_processing

def create_bigId_string(sigl: str, platform: str, tier_code: str, url: str = catalog_of_ids_url) -> str:
    return url + 'id=' + sigl + '&language=en-us&market=US&platformContext=' + platform + '&subscriptionContext=' + tier_code


def get_bigIds() -> dict:
    consoles = {platform: {tier: [] for tier in GAMEPASS_TIERS} for platform in GAMEPASS_PLATFORMS}

    for tier in GAMEPASS_TIERS:
        sigl = GAMEPASS_TIERS.get(tier).get('sigl')
        tier_code = GAMEPASS_TIERS.get(tier).get('tier_code')
    
        for platform in GAMEPASS_PLATFORMS:
            responses_of_bigIds = requests.get(create_bigId_string(sigl, platform, tier_code)).json()
            for response in responses_of_bigIds:
                if response.get('id'):
                    consoles.get(platform).get(tier).append(response.get('id'))
            
    return consoles

def create_master_set(consoles: dict) -> list:
    master_set = set()
    
    for platform in GAMEPASS_PLATFORMS:
        for tier in GAMEPASS_TIERS:
            master_set.update(consoles.get(platform).get(tier))
    
    return list(master_set)

def add_to_gamepass_table(master_set: list):
    conn = get_conn()
    list_size = 100
    
    chunked_list = [master_set[i: i + list_size] for i in range(0, len(master_set), list_size)]
    for list in chunked_list:
        list_str = ','.join(list)

        names_query = requests.get(catalog_of_titles_url + 'bigIds=' + list_str + '&market=US&languages=en-us').json()
        products = names_query['Products']

        for product in products:
            game_name = product['LocalizedProperties'][0]['ProductTitle']
            gamepass_id = product['ProductId']
            #gp_dev = product['LocalizedProperties'][0]['DeveloperName']
            #gp_pub = product['LocalizedProperties'][0]['PublisherName']
            #orig_rel_date = dt.datetime.fromtimestamp(product['MarketProperties'][0]['OriginalReleaseDate']).date().isoformat()
            #for rating in product['MarketProperties'][0]['ContentRatings']:
            #    if rating['RatingSystem'] != 'ESRB':
            #        continue
            #    else:
            #        rating_id = rating['RatingId']
            #        rating_desc = rating['RatingDescriptors']    

            conn.execute("""
                INSERT OR IGNORE INTO gamepass_catalog (gamepass_id, game_title)
                VALUES (?, ?)
            """, (gamepass_id, game_name))

    conn.commit()
    conn.close()

def update_with_tiers(consoles: dict):
    conn = get_conn()

    for platform in GAMEPASS_PLATFORMS:
        if platform == 'ConsoleGen8' or platform == 'ConsoleGen8;ConsoleGen9':
            continue

        for tier in GAMEPASS_TIERS:
            for bigID in consoles[platform][tier]:
                id_check_tuple = conn.execute("""
                    SELECT gamepass_id FROM gamepass_catalog
                    WHERE gamepass_id = ?
                """, (bigID, )).fetchone()

                id_check = id_check_tuple[0] if id_check_tuple else None

                conn.execute(f"""
                    UPDATE gamepass_catalog SET 
                        active_on_gamepass = 1,
                        {tier} = 1
                    WHERE gamepass_id = ?
                """, (id_check, ))

    conn.commit()
    conn.close()

def add_to_games_table():
    conn = get_conn()

    gamepass_items = conn.execute("""
        SELECT gamepass_id, game_title
        FROM gamepass_catalog
    """).fetchall()

    conn.close()

    for gamepass_id, game_title in gamepass_items:
        body = f"fields external_games.name, external_games.uid; search \"{game_title}\";"

        search_results = requests.post(IGDB_GAMES_ENDPOINT, headers = header, data = body).json()

        for search_result in search_results:
            if search_result.get('external_games'):
                for external_game in search_result.get('external_games'):
                    conn = get_conn()
    
                    already_added = conn.execute("""
                        SELECT gamepass_id FROM games WHERE gamepass_id = ?
                    """, (gamepass_id, )).fetchone()

                    conn.close()

                    if already_added:
                        continue

                    if external_game.get('uid') == gamepass_id:
                        igdb_id = search_result.get('id')
                        
                        conn = get_conn()

                        if not conn.execute("""
                            SELECT igdb_id FROM games WHERE igdb_id = ?
                        """, (igdb_id, )).fetchone():
                            game_processing(igdb_id)

                        conn.execute("""
                            UPDATE games SET gamepass_id = ? WHERE igdb_id = ?
                        """, (gamepass_id, igdb_id))
                            
                        conn.commit()
                        conn.close()

def main():
    consoles = get_bigIds()
    master_set = create_master_set(consoles)
    add_to_gamepass_table(master_set)
    update_with_tiers(consoles)
    add_to_games_table()

if __name__ == '__main__':
    main()