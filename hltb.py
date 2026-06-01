from config import get_conn
from howlongtobeatpy import HowLongToBeat

def get_hltb_info(game_name: str):
    hltb_results = HowLongToBeat().search(game_name)
    
    if hltb_results:
        return hltb_results
    else:
        print("No entries found for howlongtobeat. ")
        return

def add_hltb_info(
    hltb_id: int, 
    game_table_id: int, 
    hltb_main_story: float, 
    hltb_main_extras: float, 
    hltb_completionist: float, 
    hltb_all_styles: float
):
    conn = get_conn()
    
    conn.execute("""
        INSERT OR IGNORE INTO hltb_data (
            hltb_id,
            game_table_id,
            main_story,
            main_extras,
            completionist,
            all_play_styles
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        hltb_id,
        game_table_id,
        hltb_main_story,
        hltb_main_extras,
        hltb_completionist,
        hltb_all_styles
    ))
    conn.commit()
    conn.close()