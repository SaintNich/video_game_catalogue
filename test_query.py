import requests
from access_token import create_header

results = requests.post('https://api.igdb.com/v4/search', headers = create_header(), data = 'fields game, name; where name = \"Satisfactory\";').json()

print(results)