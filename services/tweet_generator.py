from openai import OpenAI
from typing import List, Dict
import config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TweetGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        logger.info("TweetGenerator initialized")

    def generate_thread(self, request: Dict) -> List[str]:
        """
        Generate a thread of tweets based on the provided parameters
        
        Args:
            request: Dictionary containing:
                - main: Main topic/TLDR
                - context: Additional context
                - keywords: Must-mention keywords
                - tag: X accounts to mention
                - length: Approximate thread length
        
        Returns:
            List of tweets for the thread
        """
        logger.info(f"Generating thread for topic: {request['main']}")
        logger.info(f"Required keywords: {request['keywords']}")
        
        prompt = self._create_prompt(request)
        logger.info("Generated prompt for OpenAI")
        logger.debug(f"Prompt content: {prompt}")
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a social media manager crafting engaging X (Twitter) threads for an event: ETHTaipei2025, which is the most eth and dev focused event in Taiwan, especially around Ethereum protocol, smart contract devs, defi and zk tech. Don't use too much emojis or hashtags"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            logger.info("Received response from OpenAI")
            
            tweets = self._parse_response(response.choices[0].message.content)
            logger.info(f"Generated {len(tweets)} tweets")
            for i, tweet in enumerate(tweets, 1):
                logger.info(f"Tweet {i}: {tweet}")
            
            return tweets
            
        except Exception as e:
            logger.error(f"Error generating tweets: {str(e)}")
            raise
    
    def _create_prompt(self, request: Dict) -> str:
        # Process tags: split if string, convert to list if None
        tags = request.get('tag')
        if tags is None:
            tag_list = []
        else:
            tag_list = [t.strip() for t in tags.split(',') if t.strip()]

        # Process keywords
        keyword_list = [k.strip() for k in request['keywords'].split(',') if k.strip()]

        prompt = f"""Create a Twitter thread with the following requirements:

Main Topic: {request['main']}
Context: {request['context']}
Required Keywords: {', '.join(keyword_list)}
{f"Accounts to Tag: {', '.join(tag_list)}" if tag_list else ""}
Approximate Thread Length: {request['length']} tweets

Format the response as a list of tweets, with each tweet starting with a number and staying within 280 characters.
Make sure to include all required keywords and tags."""
        
        logger.debug(f"Created prompt: {prompt}")
        return prompt

    def _parse_response(self, response: str) -> List[str]:
        # Split response into individual tweets
        tweets = [tweet.strip() for tweet in response.split('\n') if tweet.strip()]
        
        # Process each tweet
        cleaned_tweets = []
        for tweet in tweets:
            # Remove numbering if present
            if tweet[0].isdigit():
                tweet = tweet[tweet.find(' ')+1:].strip()
            
            # Remove any surrounding quotes
            tweet = tweet.strip('"').strip("'").strip()
            
            if tweet:  # Only add non-empty tweets
                cleaned_tweets.append(tweet)
                
        return cleaned_tweets
