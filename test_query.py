import requests
from access_token import create_header

results = requests.post('https://api.igdb.com/v4/games', headers = create_header(), data = 'fields name, collections.name; where name = \"Tomb Raider\";').json()

print(results)