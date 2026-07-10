import logging
import sqlite3

from howlongtobeatpy import HowLongToBeat

from config import get_conn

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="games.log",
)

log = logging.getLogger(__name__)


def get_hltb_info(game_name: str):
    try:
        hltb_results = HowLongToBeat().search(game_name)

    except Exception as e:
        log.error(f"Failed search of HowLongToBeat: {type(e).__name}: {e}")
        return None

    else:
        if hltb_results:
            log.debug(f"Results found from HLTB: {hltb_results}")
            return hltb_results
        else:
            log.info("No entries found for howlongtobeat. ")
            return None


def add_hltb_info(
    hltb_id: int,
    game_table_id: int,
    hltb_main_story: float,
    hltb_main_extras: float,
    hltb_completionist: float,
    hltb_all_styles: float,
) -> bool:
    conn = get_conn()

    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO hltb_data (
                hltb_id,
                game_table_id,
                main_story,
                main_extras,
                completionist,
                all_play_styles
            ) VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                hltb_id,
                game_table_id,
                hltb_main_story,
                hltb_main_extras,
                hltb_completionist,
                hltb_all_styles,
            ),
        )

    except sqlite3.Error as e:
        log.error(
            f"An operation to the hltb_data table failed: {type(e).__name__}: {e}"
        )
        conn.rollback()
        return False
    
    else:
        conn.commit()
        return True

    finally:
        conn.close()
