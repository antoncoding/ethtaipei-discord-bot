import requests
import logging
import config

logger = logging.getLogger(__name__)

class TweetScheduler:
    def __init__(self):
        self.base_url = "https://api.typefully.com/v1/drafts/"  # Updated endpoint
        self.headers = {
            "X-API-KEY": f"Bearer {config.TYPEFULLY_API_KEY}",  # Updated header
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Python/3.10"
        }

    def schedule_thread(self, tweets):
        """
        Create a draft thread on Typefully.
        
        Args:
            tweets (list): List of tweet texts to be posted
            
        Returns:
            str: URL to the draft on Typefully
        """
        try:
            # Prepare the request body
            body = {
                "content": "\n\n\n\n".join(tweets),  # Use 4 newlines as in test
                "threadify": True,
                "share": True
            }
            
            response = requests.request(
                method='POST',
                url=self.base_url,
                headers=self.headers,
                json=body,
                allow_redirects=True
            )
            response.raise_for_status()
            
            data = response.json()
            if not data:
                raise ValueError("Empty response from Typefully API")
            
            # Get share URL or construct it from draft ID
            share_url = data.get('share_url')
            if not share_url and 'id' in data:
                share_url = f"https://typefully.com/draft/{data['id']}"
            
            if not share_url:
                raise ValueError("No URL in Typefully response")
                
            logger.info(f"Draft thread created successfully on Typefully")
            return share_url
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating draft on Typefully: {str(e)}")
            raise Exception(f"Failed to create draft: {str(e)}")
        except ValueError as e:
            logger.error(f"Invalid response from Typefully: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in schedule_thread: {str(e)}")
            raise
