import requests

url = "https://api.upcitemdb.com/prod/trial/lookup?upc=5014293150286"
response = requests.get(url, timeout=5)
print(response.status_code)
print(response.text)
