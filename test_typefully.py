import requests
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()
api_key = os.getenv('TYPEFULLY_API_KEY')

# API configuration
url = 'https://api.typefully.com/v1/drafts/'
headers = {
    'X-API-KEY': f'Bearer {api_key}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'User-Agent': 'Python/3.10'
}

# Test tweet data
data = {
    'content': 'Test tweet from API\n\n\n\nSecond tweet in thread',
    'threadify': True,
    'share': True
}

try:
    # Make request
    response = requests.request(
        method='POST',
        url=url,
        headers=headers,
        json=data,
        allow_redirects=True
    )
    
    print(f'Status code: {response.status_code}')
    if response.text:
        response_json = response.json()
        print(f'\nResponse: {json.dumps(response_json, indent=2)}')
        if response_json.get('share_url'):
            print(f'\nShare URL: {response_json["share_url"]}')
    
except Exception as e:
    print(f'Error: {str(e)}')
