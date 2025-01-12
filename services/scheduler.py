import requests
from typing import List
import config
from datetime import datetime

class TweetScheduler:
    def __init__(self):
        self.api_key = config.TYPEFULLY_API_KEY
        self.base_url = "https://api.typefully.com"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

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
        
        # Create draft in Typefully
        response = requests.post(
            f"{self.base_url}/v1/drafts",
            headers=self.headers,
            json={
                "content": "\n\n".join(tweets),
                "schedule": schedule_time.isoformat()
            }
        )
        
        response.raise_for_status()
        draft_data = response.json()
        
        # Return the Typefully draft URL
        return f"https://typefully.com/draft/{draft_data['id']}"
