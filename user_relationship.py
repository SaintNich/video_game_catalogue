import datetime as dt
import logging
import sqlite3

from config import get_conn

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

log = logging.getLogger(__name__)


def create_user_game_relationship(game_table_id: int, hours_played: float = 0.0):
    conn = get_conn()
    try:
        today = dt.datetime.now().date().isoformat()

        relationship_id_tuple = conn.execute(
            """
            SELECT relationship_id FROM user_game_relationship
            WHERE game_table_id = ?
        """,
            (game_table_id,),
        ).fetchone()

        relationship_id = relationship_id_tuple[0] if relationship_id_tuple else None

        if not relationship_id:
            conn.execute(
                """
                INSERT OR IGNORE INTO user_game_relationship (game_table_id, date_added, hours_played)
                VALUES (?, ?, ?)
            """,
                (game_table_id, today, hours_played),
            )
            conn.commit()
            log.info(
                f"user_game_relationship created successfully for game_table_id = {game_table_id}"
            )
            return True
        else:
            log.info(
                f"user_game_relationship already exists for game_table_id = {game_table_id}"
            )
            return False

    except sqlite3.Error as e:
        log.error(
            f"An operation to the user_game_relationship table failed: {type(e).__name__}: {e}"
        )
        conn.rollback()
        return None

    finally:
        conn.close()


# def main():
#    # unpack variables from create_user_game_relationship()
#    game_table_id, relationship_id, update_selection = create_user_game_relationship()
#
#    # run appropriate function based on selection
#    if update_selection:
#        match update_selection:
#            case 1:
#                print("You've chosen to update your ownership status. ")
#                game_ownership(game_table_id, relationship_id)
#            case 2:
#                print("You've chosen to update where you've played this game. ")
#                game_played(game_table_id, relationship_id)
#            case 3:
#                print("You've chosen to update your game catalog status. ")
#                update_user_game_relationship(relationship_id, 3)
#            case 4:
#                print("You've chosen to update completion dates. ")
#                update_user_game_relationship(relationship_id, 4)
#            case 5:
#                print("You've chosen to update your time played. ")
#                update_user_game_relationship(relationship_id, 5)
#            case 6:
#                print("You've chosen to update your rating of this game. ")
#                update_user_game_relationship(relationship_id, 6)
#            case 7:
#                print("You've chosen to add notes to this game. ")
#                update_user_game_relationship(relationship_id, 7)
#            case _:
#                print("You didn't make an appropriate selection, please try again.")
#
# if __name__ == '__main__':
#    main()
