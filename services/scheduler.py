import requests
from typing import List
from datetime import datetime
import config
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TweetScheduler:
    def __init__(self):
        self.api_key = config.TYPEFULLY_API_KEY
        if not self.api_key:
            raise ValueError("TYPEFULLY_API_KEY is not set in environment variables")
            
        self.base_url = "https://api.typefully.com"
        self.headers = {
            "X-API-KEY": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Python/3.10"
        }
        logger.info("TweetScheduler initialized successfully")

    def schedule_thread(self, tweets: List[str], deadline: str) -> str:
        """
        Schedule a thread of tweets using Typefully API
        
        Args:
            tweets: List of tweets to schedule
            deadline: Deadline in ISO format
        
        Returns:
            Typefully share URL
        """
        schedule_time = datetime.fromisoformat(deadline)
        content = "\n\n\n\n".join(tweets)
        
        request_data = {
            "content": content,
            "schedule-date": schedule_time.isoformat(),
            "threadify": True,
            "share": True
        }

        try:
            endpoint = f"{self.base_url}/v1/drafts/"
            response = requests.request(
                method='POST',
                url=endpoint,
                headers=self.headers,
                json=request_data,
                allow_redirects=True
            )
            
            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                raise Exception(f"API returned status code {response.status_code}")
            
            if not response.text:
                raise Exception("Empty response from Typefully API")
            
            draft_data = response.json()
            share_url = draft_data.get('share_url')
            if not share_url:
                share_url = f"https://typefully.com/draft/{draft_data['id']}"
            
            logger.info(f"Thread scheduled successfully: {share_url}")
            return share_url
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise Exception("Failed to schedule tweets") from e
        except json.JSONDecodeError as je:
            logger.error(f"Invalid API response: {str(je)}")
            raise Exception("Invalid response from API") from je
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise
