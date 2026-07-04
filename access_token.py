import datetime as dt
import json
import os

import requests

from config import CLIENT_ID, CLIENT_SECRET, GRANT_TYPE

ACCESS_TOKEN_FILE = "access_token.json"
TOKEN_BUFFER = 3


# if file doesn't exist, creates the JSON with the access_token information
def create_access_token_file():
    now = dt.datetime.now()
    igdb_access_url = (
        "https://id.twitch.tv/oauth2/token?client_id="
        + CLIENT_ID
        + "&client_secret="
        + CLIENT_SECRET
        + "&grant_type="
        + GRANT_TYPE
    )
    response = requests.post(igdb_access_url).json()
    response.update({"acquired_on": str(now)})
    with open(ACCESS_TOKEN_FILE, "w") as f:
        json.dump(response, f)
    print("access_token file created/updated")


# obtains access token from access_token.json
def get_access_token_from_file():
    with open(ACCESS_TOKEN_FILE, "r") as f:
        access_token_json = json.load(f)
    return access_token_json


# checks validity of access_token
def check_access_token_expiration():
    dt_time_format = "%Y-%m-%d %H:%M:%S.%f"
    access_token_json = get_access_token_from_file()

    # look up date acquired
    acquired = access_token_json.get("acquired_on")

    # looks up expiration value in seconds
    expires = access_token_json.get("expires_in")
    now = dt.datetime.now()

    # calculate expiration date by adding the expires_in value to the date acquired
    exp_date = dt.datetime.strptime(acquired, dt_time_format) + dt.timedelta(
        seconds=expires
    )

    # calculate the time remaining until expiration
    time_remaining = exp_date - now

    return time_remaining.days


def get_access_token():
    try:
        # checks if the access_token.json file exists and if the access_token is valid
        if (
            os.path.exists(ACCESS_TOKEN_FILE)
            and check_access_token_expiration() >= TOKEN_BUFFER
        ):
            access_token = get_access_token_from_file()
            # returns the access_token itself, not the other parts of the file
            return access_token.get("access_token")

        else:
            # if not valid, or doesn't exist, access_token_file is created/updated
            print(
                "Access token file does not exist or is no longer valid, creating/updating"
            )
            create_access_token_file()
    except FileNotFoundError as e:
        print(f"Could not find {ACCESS_TOKEN_FILE}: {e}")
    except Exception as e:
        print(f"Error {e} found, view traceback.")


def create_header():
    ACCESS_TOKEN = get_access_token()
    HEADER = {"Client-ID": CLIENT_ID, "Authorization": "Bearer " + ACCESS_TOKEN}

    return HEADER
