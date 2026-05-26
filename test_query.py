import requests
from howlongtobeatpy import HowLongToBeat

results = HowLongToBeat().search_from_id(7231)

print(results.game_name)

for result in dir(results):
    print(result)