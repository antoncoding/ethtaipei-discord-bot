from openai import OpenAI
from typing import List, Dict
import config

class TweetGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)

    def generate_thread(self, request: Dict) -> List[str]:
        """
        Generate a thread of tweets based on the provided parameters
        
        Args:
            request: Dictionary containing:
                - main: Main topic/TLDR
                - context: Additional context/requirements
                - keywords: Must-mention keywords
                - tag: X accounts to mention
                - deadline: Posting deadline
                - length: Approximate thread length
        
        Returns:
            List of tweets for the thread
        """
        prompt = self._create_prompt(request)
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional social media manager crafting engaging X (Twitter) threads."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        # Parse the response and return list of tweets
        return self._parse_response(response.choices[0].message.content)
    
    def _create_prompt(self, request: Dict) -> str:
        return f"""Create a Twitter thread with the following requirements:

Main Topic: {request['main']}
Context: {request['context']}
Required Keywords: {', '.join(request['keywords'])}
Accounts to Tag: {', '.join(request['tag'])}
Approximate Thread Length: {request['length']} tweets
Deadline: {request['deadline']}

Format the response as a list of tweets, with each tweet starting with a number and staying within 280 characters.
Make sure to include all required keywords and tags.
Make the thread engaging and professional."""

    def _parse_response(self, response: str) -> List[str]:
        # Split response into individual tweets and clean them
        tweets = [tweet.strip() for tweet in response.split('\n') if tweet.strip()]
        # Remove numbering if present and clean up
        tweets = [tweet[tweet.find(' ')+1:] if tweet[0].isdigit() else tweet for tweet in tweets]
        return tweets
