import requests
response = requests.get('https://catalog.gamepass.com/sigls/v3?id=97c6c862-d28a-4907-a3d5-c401f2296a53&language=en-us&market=US&platformContext=ConsoleGen8;ConsoleGen9&subscriptionContext=cfq7ttc0khs0').json()
response1 = (response[1].get('id'))

big_ID_response = requests.get('https://displaycatalog.mp.microsoft.com/v7.0/products?bigIds=' + response1 + '&market=US&languages=en-us').json()
print(big_ID_response.get('ProductTitle'))