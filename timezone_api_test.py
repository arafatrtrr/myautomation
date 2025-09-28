import requests
import json

ip_address = "103.152.104.95"
url = "https://ip-score.com/json"
data = {'ip': ip_address}

try:
    response = requests.post(url, data=data)
    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    
    json_response = response.json()
    
    if json_response:
        print(json.dumps(json_response, indent=4))
    else:
        print("No data received from the API.")

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
except json.JSONDecodeError:
    print("Failed to decode JSON response.")