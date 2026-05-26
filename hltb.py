from config import get_conn
from howlongtobeatpy import HowLongToBeat

def process_hltb_info(game_name: str, game_table_id: int):
    conn = get_conn()
    hltb_results = HowLongToBeat().search(game_name)

    if hltb_results:
        for i, result in enumerate(hltb_results):
            hltb_name = result.game_name
            hltb_release_world = result.release_world

            print(f"{i+1}. {hltb_name} released in {hltb_release_world}")

        try:
            while True:
                confirm_selection = input("Which game are you getting the howlongtobeat data for? ")
                confirm_int = int(confirm_selection)

                if 1 <= confirm_int <= len(hltb_results):
                    break
                print("Be sure to choose a number from the list. ")

            confirmed_selection = hltb_results[confirm_int - 1]
            hltb_id = confirmed_selection.game_id
            hltb_main_story = confirmed_selection.main_story
            hltb_main_extras = confirmed_selection.main_extra
            hltb_completionist = confirmed_selection.completionist
            hltb_all_styles = confirmed_selection.all_styles        
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

        except ValueError:
            print("Please enter an integer")
            return process_hltb_info(game_name, game_table_id)
    else:
        print("No entries found for howlongtobeat. ")
        return