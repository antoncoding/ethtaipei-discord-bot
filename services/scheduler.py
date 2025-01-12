import requests
from typing import List
from datetime import datetime
import config
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TweetScheduler:
    def __init__(self):
        self.api_key = config.TYPEFULLY_API_KEY
        if not self.api_key:
            logger.error("No Typefully API key found in environment variables!")
            raise ValueError("TYPEFULLY_API_KEY is not set in environment variables")
            
        self.base_url = "https://api.typefully.com/v1"
        self.headers = {
            "X-API-KEY": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"TweetScheduler initialized with API key: {self.api_key[:5]}...")
        logger.debug(f"Full headers: {self.headers}")
        logger.debug(f"Current environment: {dict(os.environ)}")

    def schedule_thread(self, tweets: List[str], deadline: str) -> str:
        """
        Schedule a thread of tweets using Typefully API
        
        Args:
            tweets: List of tweets to schedule
            deadline: Deadline in human-readable format
        
        Returns:
            Typefully draft URL
        """
        # Convert deadline to ISO format
        schedule_time = datetime.fromisoformat(deadline)
        logger.info(f"Scheduling thread for: {schedule_time.isoformat()}")
        logger.info(f"Number of tweets to schedule: {len(tweets)}")
        logger.debug(f"Tweet content: {tweets}")

        # Prepare request data
        request_data = {
            "content": "\n\n\n\n".join(tweets),  # 4 newlines as per docs
            "schedule-date": schedule_time.isoformat(),
            "threadify": True,
            "share": True
        }
        logger.info("Prepared request data")
        logger.debug(f"Request data: {request_data}")
        logger.debug(f"Using headers: {self.headers}")

        try:
            endpoint = f"{self.base_url}/drafts"  # Removed trailing slash
            logger.info(f"Making POST request to {endpoint}")
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=request_data
            )
            
            logger.info(f"Response status code: {response.status_code}")
            logger.debug(f"Response content: {response.text}")
            
            response.raise_for_status()
            draft_data = response.json()
            
            share_url = draft_data.get('share_url')
            if not share_url:
                logger.warning("No share_url in response, falling back to draft URL")
                share_url = f"https://typefully.com/draft/{draft_data['id']}"
            
            logger.info(f"Draft created successfully with URL: {share_url}")
            return share_url
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error scheduling tweets: {str(e)}")
            logger.error(f"Response content: {getattr(e.response, 'text', 'No response content')}")
            logger.error(f"Request headers used: {self.headers}")
            raise Exception(f"Failed to schedule tweets: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise
