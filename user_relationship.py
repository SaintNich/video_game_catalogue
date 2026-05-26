import datetime as dt
from config import get_conn

# Defined the different relationship update options
relationship_updates = {
    'update_types': {
        1: 'Ownership update',
        2: 'Where played update',
        3: 'Game catalog status',
        4: 'Game completion update',
        5: 'Time played update',
        6: 'Game rating update',
        7: 'User notes update',
        0: 'No updates at this time'
    }
}

yes_or_no_confirmation = 'Please enter yes or no (y or n).'

def create_user_game_relationship () -> tuple[int, int, int]:
    conn = get_conn()
    game_selection = input("Enter a game you would like to establish a relationship for: ")
    today = dt.datetime.now().date().isoformat()

    # extract game_table_id from games
    game_table_id_tuple = conn.execute("""
        SELECT game_table_id FROM games
        WHERE title LIKE ?
    """, ('%' + game_selection + '%', )).fetchone()

    # isolate the game_table_id from the tuple
    game_table_id = game_table_id_tuple[0] if game_table_id_tuple else None

    # extract the title stored in the games table
    actual_title_tuple = conn.execute("""
        SELECT title FROM games
        WHERE game_table_id = ?
    """, (game_table_id, )).fetchone()

    # extract the relationship_id
    relationship_id_tuple = conn.execute("""
        SELECT relationship_id FROM user_game_relationship
        WHERE game_table_id = ?
    """, (game_table_id, )).fetchone()

    # isolate the ids from the tuples
    actual_title = actual_title_tuple[0] if actual_title_tuple else None
    relationship_id = relationship_id_tuple[0] if relationship_id_tuple else None

    # check if relationship_id exists and define relationship_update based on result
    if relationship_id:
        relationship_update = input(f"Relationship already exists for {actual_title}. Do you wish to update that relationship? ").lower()
    else:
        # if relationship_id does not exist, create entry into user_game_relationship
        conn.execute("""
            INSERT OR IGNORE INTO user_game_relationship (game_table_id, date_added)
            VALUES (?, ?)
        """, (game_table_id, today))

        relationship_update = input(f"Relationship established for {actual_title} effective {today}. Would you like to make any other updates to the relationship? ").lower()

    conn.commit()
    conn.close()

    # make sure user only enters an acceptable version of yes or no
    while True:
        if relationship_update == 'yes' or relationship_update == 'y' or relationship_update == 'no' or relationship_update == 'n':
            break
        print(yes_or_no_confirmation)

    if relationship_update == 'yes' or relationship_update == 'y':
        # display list of update types in console if user chooses to make updates          
        for update_type, update in relationship_updates.get('update_types').items():            
            print(f"{update_type}: {update}")        
    else:
        print("You chose not to make any other updates. ")
        update_selection = 0
        return game_table_id, relationship_id, update_selection

    # make sure user only inters a valid entry, this time including 0 as an option
    while True:
        update_selection = input("What type of update would you like to make? ")

        if 0 <= int(update_selection) <= len(relationship_updates.get('update_types')):
            break
        print("Please make a valid selection from the list. ")

    # make the inputted string an integer
    update_selection = int(update_selection)

    if update_selection == 0:
        print(f"Cancelled update for {actual_title}. ")
        return game_table_id, relationship_id, update_selection
    else:
        return game_table_id, relationship_id, update_selection
    
def game_ownership(game_table_id: int, relationship_id: int):
    conn = get_conn()

    # extract platform_id and platform from platforms based on game_table_id
    game_tables = conn.execute("""
        SELECT p.platform_id, p.platform
        FROM game_platforms g
        JOIN platforms p
        ON g.platform_id = p.platform_id    
        WHERE g.game_table_id = ?
    """, (game_table_id, )).fetchall()

    # for each platform, check ownership
    for platform_id, platform in game_tables:
        own_prompt = input(f"Do you own the game on {platform}? Yes or No" ).lower()

        while True:
            if own_prompt == 'yes' or own_prompt == 'y' or own_prompt == 'no' or own_prompt == 'n':
                break
            print(yes_or_no_confirmation)

        # if owned, update user_platform_own
        if own_prompt == 'yes' or own_prompt == 'y':
            conn.execute("""
                INSERT OR IGNORE INTO user_platform_own (relationship_id, platform_id)
                VALUES (?, ?)
            """, (relationship_id, platform_id))

    conn.commit()
    conn.close()

def game_played(game_table_id: int, relationship_id: int):
    conn = get_conn()

    # extract platform_id and platform from platforms based on game_table_id
    game_tables = conn.execute("""
        SELECT p.platform_id, p.platform
        FROM game_platforms g
        JOIN platforms p
        ON g.platform_id = p.platform_id    
        WHERE g.game_table_id = ?
    """, (game_table_id, )).fetchall()

    # for each platform, check if played
    for platform_id, platform in game_tables:
        played_prompt = input(f"Have you played the game on {platform}? Yes or No" ).lower()

        while True:
            if played_prompt == 'yes' or played_prompt == 'y' or played_prompt == 'no' or played_prompt == 'n':
                break
            print(yes_or_no_confirmation)

        # if played, update user_played_on
        if played_prompt == 'yes' or played_prompt == 'y':
            conn.execute("""
                INSERT OR IGNORE INTO user_played_on (relationship_id, platform_id, game_hours)
                VALUES (?, ?, 0) 
            """, (relationship_id, platform_id))
            # Need to update game_hours automatically from Steam or manually.

    conn.commit()
    conn.close()

def update_catalog_status() -> str:
    # dict of types of statuses (migrated wishlist to a status instead of it's own function)
    catalog_statuses = {
        1: 'Backlog',
        2: 'In-Progress',
        3: 'Completed Main Story',
        4: 'Completed Fully',
        5: 'Abandoned',
        6: 'On Hold',
        7: 'New Game+',
        8: 'Wishlisted'
    }

    # display list of play statuses
    for i, catalog_status in catalog_statuses.items():
        print(f"{i}. {catalog_status}")

    status_choice = input("Please make a selection for the updated status. ")

    # make sure user only inters a valid entry
    while True:
        if 1 <= int(status_choice) <= len(catalog_statuses):
            break
        print("Please make a valid selection from the list. ")

    updated_status = catalog_statuses[int(status_choice)]
    
    return updated_status

def date_formatter_from_input(provided_date: str):
    formatted_date = dt.datetime.strptime(provided_date, '%Y/%m/%d')
    return formatted_date

def update_game_completion() -> str:
    type_of_completion = input("Is this an update of the main story line completion? Or a full completionist update? ").lower()

    # validate an expected entry only
    while True:
        if type_of_completion == 'main' or type_of_completion == 'main story' or type_of_completion == 'main story line' or type_of_completion == 'full' or type_of_completion == 'full story' or type_of_completion == 'full completion':
            break
        print("Please enter main, main story, main story line, full, full story, or full completion")

    # update type of completion based on selection and process date of completion
    if type_of_completion == 'main' or type_of_completion == 'main story' or type_of_completion == 'main story line':
        type_of_completion = 'main'
        date_of_main_complete = date_formatter_from_input(input("What date did you complete the main story line? (format MM-DD-YYYY) "))
        print(f"You completed the main story on {date_of_main_complete}. ")
        return type_of_completion, date_of_main_complete
    else:
        type_of_completion = 'full'
        date_of_full_complete = date_formatter_from_input(input("What date did you fully complete this game? (format MM-DD-YYYY) "))
        print(f"You fully completed the game on {date_of_full_complete}. ")
        return type_of_completion, date_of_full_complete

def update_hours_played(relationship_id: int) -> float:
    conn = get_conn()

    # extract the current play time stored
    current_play_time_tuple = conn.execute("""
        SELECT hours_played FROM user_game_relationship
        WHERE relationship_id = ?
    """, (relationship_id, )).fetchone()

    current_play_time = current_play_time_tuple[0] if current_play_time_tuple else 0

    add_play_time = input(f"Your current play time is {current_play_time}. How much time would you like to add? ")

    updated_play_time = float(current_play_time) + float(add_play_time)

    conn.close()
    return updated_play_time

def update_rating() -> float:
    game_rating = float(input("How many stars do you give this game? Please enter 0 (worst) to 5 (best). Values can be decimals. "))

    # validate rating is between 0 and 5
    while True:
        if game_rating >= 0 and game_rating <= 5:
            break
        print("Please enter a value between 0 and 5. ")

    return game_rating

def update_user_notes() -> str:
    game_notes = input("What notes would you like to provide for this game? ")

    if game_notes == '':
        print("You chose not to enter any additional notes. ")
        return
    
    return game_notes

def update_user_game_relationship(relationship_id: int, update_selection: int):
    match update_selection:
        case 3:
            column_to_update = 'catalog_status'
            value_to_update = update_catalog_status()
        case 4:
            game_completion_type, game_completion_date = update_game_completion()
            if game_completion_type == 'main':
                column_to_update = 'date_main_completed'
            else:
                column_to_update = 'date_completed'
            value_to_update = game_completion_date
        case 5:
            column_to_update = 'hours_played'
            value_to_update = update_hours_played()
        case 6:
            column_to_update = 'rating'
            value_to_update = update_rating()
        case 7:
            column_to_update = 'user_notes'
            value_to_update = update_user_notes()

    conn = get_conn()

    # update user_game_relationship table based on the case
    conn.execute(f"""
        UPDATE user_game_relationship
        SET {column_to_update} = ?
        WHERE relationship_id = ?
    """, (value_to_update, relationship_id))

    conn.commit()
    conn.close()

def main():
    # unpack variables from create_user_game_relationship()
    game_table_id, relationship_id, update_selection = create_user_game_relationship()

    # run appropriate function based on selection
    if update_selection:
        match update_selection:
            case 1:
                print("You've chosen to update your ownership status. ")
                game_ownership(game_table_id, relationship_id)
            case 2:
                print("You've chosen to update where you've played this game. ")
                game_played(game_table_id, relationship_id)
            case 3:
                print("You've chosen to update your game catalog status. ")
                update_user_game_relationship(relationship_id, 3)
            case 4:
                print("You've chosen to update completion dates. ")
                update_user_game_relationship(relationship_id, 4)
            case 5:
                print("You've chosen to update your time played. ")
                update_user_game_relationship(relationship_id, 5)
            case 6:
                print("You've chosen to update your rating of this game. ")
                update_user_game_relationship(relationship_id, 6)
            case 7:    
                print("You've chosen to add notes to this game. ")
                update_user_game_relationship(relationship_id, 7)
            case _:
                print("You didn't make an appropriate selection, please try again.")

if __name__ == '__main__':
    main()