import requests
import re
import json

url = "https://raw.githubusercontent.com/alex4528x/m3u/refs/heads/main/jtv.m3u"
try:
    response = requests.get(url, timeout=10)
    lines = response.text.splitlines()
    print("Fetched nicely. Total lines:", len(lines))
except Exception as e:
    print("Failed to fetch via original URL:", e)
    url = "https://cdn.jsdelivr.net/gh/alex4528x/m3u@main/jtv.m3u"
    response = requests.get(url)
    lines = response.text.splitlines()
    print("Fetched via proxy. Total lines:", len(lines))

count = 0
current_key_id = "default_id"
current_key = "default_key"

for line in lines[:500]:  # Just check first 500 lines to see if we see adaptive.license_key
    line = line.strip()
    if 'adaptive.license_key=' in line:
        print("Found key line:", line)
        parts = line.split('adaptive.license_key=')
        if len(parts) > 1:
            keys = parts[1].strip()
            # It could look like: `123123:123123` or `{"keys":[{"kty":"oct","k":"...","kid":"..."}]}`
            print(f" Extracted keys string: {keys}")
    elif line.startswith("https://") and ".mpd" in line:
        print(" Found mpd stream:", line)
        print("----")
            