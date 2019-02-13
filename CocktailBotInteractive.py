from CocktailBot import CocktailBot
from pymongo import MongoClient
import time, os

class CocktailBotInteractive(CocktailBot):

    def __init__(self):
        super().__init__()
        self.POLLING_SLEEP_TIME = 20
        self.MENTIONS_PER_QUERY = 10
        self.USERNAME = "@cocktailsbot"
        database = MongoClient(os.environ["MONGO_STRING"].strip())
        self.DATABASE = database[os.environ["MONGO_DATABASE"].strip()]["MentionsHistory"]
        self.QUERY_BY_INGREDIENT_PATTERN = "make me something with"
        self.QUERY_BY_NAME_PATTERN = "make me a"
        self.SOMETHING_WENT_WRONG_REPLY = "Something went wrong. Either you used the wrong syntaxis (check the pinned tweet), or there are no results for your query."


    def poll_results(self):
        # Extract minimum necessary information from last mentions
        mentions = self.TWITTER.statuses.mentions_timeline(count=10, include_entities=False)
        return mentions

    
    def is_result_processed(self, tweet_id):
        # Check if mention has been processed before
        count = self.DATABASE.count_documents({ "id": tweet_id })
        return True if count > 0 else False


    def flag_result_processed(self, tweet_id):
        # Mark current request as already processed
        self.DATABASE.insert_one({ "id": tweet_id })


    def execute_action(self, text):
        # Check which action the mention tries to trigger, if any
        action = None
        if self.QUERY_BY_INGREDIENT_PATTERN in text:
            action = ("ingredient", self.QUERY_BY_INGREDIENT_PATTERN)
        elif self.QUERY_BY_NAME_PATTERN in text:
            action = ("name", self.QUERY_BY_NAME_PATTERN)
        else:
            return None

        # Generate answer tweet(s)
        parameters = text.replace(action[1], "").strip().split()
        if "n" in parameters: parameters.remove("n")
        data = self.get_cocktail(action[0], parameters)
        content = self.extract(data)
        answer = self.process(content)

        return answer


    def listen(self):
        while True:
            results = self.poll_results()

            # Process mentions
            for result in results:
                tweet_id = result["id"]
                tweet_user = result["user"]["screen_name"]
                tweet_text = result["text"].lower().replace(self.USERNAME, "").strip()

                # Check if request has been fulfilled
                if self.is_result_processed(tweet_id):
                    log = "Tweet {} by {} was already processed ({})".format(tweet_id, tweet_user, tweet_text)
                    print(log.encode('utf-8'))
                    continue

                log = "Processing tweet {} by {} ({})".format(tweet_id, tweet_user, tweet_text)
                print(log.encode('utf-8'))

                try:
                    # Try to satisfy user's query (or discard if it's regular comment)
                    answer = self.execute_action(tweet_text)
                    if answer:
                        # Tweets need explicit @ mention, even if it doesn't increase count
                        answer["sheet"] = "@{}\n{}".format(tweet_user, answer["sheet"])
                        answer["instructions"] = ["@{} {}".format(tweet_user, instruction) for instruction in answer["instructions"]]
                        self.post_tweet(answer, in_reply_to=tweet_id)
                except Exception as e:
                    print(e)
                    # Notify user that query could not be fulfilled
                    response = "@{} {}".format(tweet_user, self.SOMETHING_WENT_WRONG_REPLY)
                    self.TWITTER.statuses.update(status=response, in_reply_to=tweet_id)
                    pass

                # Log process completed
                self.flag_result_processed(tweet_id)

            print("Sleeping...")
            time.sleep(self.POLLING_SLEEP_TIME)


if __name__ == "__main__":
    CocktailBotInteractive().listen()