from urllib import request
import json, shutil, datetime, os, time, random
from twitter import Twitter, OAuth
from emojis import EMOJI_MAP

MAX_RETIRES = 5
SLEEP_BETWEEN_RETRIES = 10
MAX_TWEET_LENGTH = 280
LOG_FILE = "log.txt"

class CocktailBot:

    def __init__(self):
        self.DIRECTORY_THUMBNAILS = "thumbnails"
        self.TWITTER_AUTH = OAuth(
            os.environ["ACCESS_KEY"].strip(),
            os.environ["ACCESS_SECRET"].strip(),
            os.environ["CONSUMER_KEY"].strip(),
            os.environ["CONSUMER_SECRET"].strip()
        )
        self.TWITTER = Twitter(auth=self.TWITTER_AUTH)
        self.HASHTAGS = "#cocktail #drink #recipe #bar"
        self.API_ENDPOINTS = {
            "random": "http://www.thecocktaildb.com/api/json/v1/1/random.php",
            "name": "https://www.thecocktaildb.com/api/json/v1/1/search.php?s=",
            "ingredient": "https://www.thecocktaildb.com/api/json/v1/1/filter.php?i=",
            "lookup": "https://www.thecocktaildb.com/api/json/v1/1/lookup.php?i="
        }


    def call_api(self, url):
        # Compose request, get content and process JSON
        url_request = request.Request(url)
        response = request.urlopen(url_request).read()
        cocktail = response.decode("utf-8")
        results = json.loads(cocktail)["drinks"]
        choice = random.choice(results)

        return choice


    def get_cocktail(self, mode="random", parameters=None):
        # Compose correct URL
        url = self.API_ENDPOINTS[mode]
        if parameters:
            url += "+".join(parameters)

        # Access API
        choice = self.call_api(url)

        # Random and name modes return drinks
        if mode == "random" or mode == "name":
            return choice

        # Ingredient mode returns drink ids, requiring one more step
        drink_url = self.API_ENDPOINTS["lookup"] + choice["idDrink"]
        choice = self.call_api(drink_url)
        
        return choice

    
    def extract_name(self, data):
        # Safely return the drink's name
        candidate = data["strDrink"]
        if not candidate:
            raise ValueError("No name")
        
        return candidate
        
        
    def extract_instructions(self, data):
        # Safely return the instructions
        candidate = data["strInstructions"]
        if not candidate:
            raise ValueError("No instructions")
        
        return candidate
        
        
    def extract_alcoholic(self, data):
        # Safely return the drink type
        candidate = data["strAlcoholic"]
        if not candidate:
            raise ValueError("No alcohol specification")
        
        return candidate
    
        
    def extract_glass(self, data):
        # Safely return the glass type
        candidate = data["strGlass"]
        if not candidate:
            raise ValueError("No glass specification")
        
        return candidate
        

    def extract_ingredients(self, data):
        # Generate list of <ingredient> <quantity> strings
        ingredients = []
        for i in range(15):
            ingredientKey, measureKey = "strIngredient{}".format(i + 1), "strMeasure{}".format(i + 1)
            ingredient = data[ingredientKey]
            if not ingredient:
                break
            measure = data[measureKey]
            ingredients.append((measure.rstrip(), ingredient))

        return ingredients
        
        
    def extract_thumbnail(self, data):
        # Safely return the thumbnail's URL
        candidate = data["strDrinkThumb"]
        if not candidate:
            raise ValueError("No thumbnail specification")
        return candidate
        
        
    def download_thumbnail(self, url):
        # Download thumbnail to drive
        filePath = "{}/{}".format(self.DIRECTORY_THUMBNAILS, url.split("/")[-1])
        with request.urlopen(url) as image, open(filePath, "wb") as file:
            shutil.copyfileobj(image, file)
        return filePath
        
        
    def introduce_emojis(self, ingredients):
        emojified = []
        for measure, ingredient in ingredients:
            ingredient_line = "{} {}".format(measure, ingredient).strip()
            # Check if ingredient is in emoji map
            if ingredient in EMOJI_MAP.keys():
                emojified.append("{} {}".format(EMOJI_MAP[ingredient].strip(), ingredient_line))
            # Assign default emoji otherwise
            else:
                emojified.append("{} {}".format(EMOJI_MAP["default"].strip(), ingredient_line))

        return emojified
        
        
    def modify_instructions(self, instructions):
        # Add decorative details to tweet
        return "{} Enjoy!{}".format(instructions, EMOJI_MAP["enjoy"])


    def build_main(self, name, alcoholic, ingredients, glass):
        # Compose main recipe tweet in a single string
        tweet = "{} ({})".format(name, alcoholic)
        glassString = "{} {}".format(EMOJI_MAP["glass"], glass.lstrip())
        tweet = "{}\n{}".format(tweet, glassString)
        for ingredient in ingredients:
            tweet = "{}\n{}".format(tweet, ingredient)
        tweet = "{}\n{}".format(tweet, self.HASHTAGS)
        
        return tweet
        
        
    def split_instructions(self, text):
        # Ensure tweet is right length
        if len(text) <= MAX_TWEET_LENGTH:
            return [text]
        
        # Break instructions in tweets, without breaking sentences
        tweets = [""]
        sentences = [s.strip() + "." for s in text.split(".")]

        for sentence in sentences:
            # For now, we assume that no sentence is longer than a tweet.
            if len(sentence) > MAX_TWEET_LENGTH:
                raise ValueError("The splitter needs updating!")
            if sentence == ".":
                continue
            # If current sentence makes tweet overflow, we start new tweet
            if len("{} {}".format(tweets[-1], sentence)) > MAX_TWEET_LENGTH:
                tweets.append("")
            tweets[-1] = "{} {}".format(tweets[-1], sentence)
            
        return tweets
        

    def post_tweet(self, tweet, in_reply_to=None):
        # Upload image to Twitter servers (we obtain ID)
        with open(tweet["image"], "rb") as file:
            image = file.read()
        uploader = Twitter(domain="upload.twitter.com", auth=self.TWITTER_AUTH)
        identifier = uploader.media.upload(media=image)["media_id_string"]
        
        # Post main tweet with ingredients
        if in_reply_to:
            result = self.TWITTER.statuses.update(status=tweet["sheet"], media_ids=identifier, in_reply_to_status_id=in_reply_to)
        else:
            result = self.TWITTER.statuses.update(status=tweet["sheet"], media_ids=identifier)
        
        # Post as many instruction replies as necessary
        for instruction in tweet["instructions"]:
            result = self.TWITTER.statuses.update(status=instruction, in_reply_to_status_id=result["id_str"])

        
    def extract(self, data):
        # Full result extraction pipeline
        return {
            "name": self.extract_name(data),
            "instructions": self.extract_instructions(data),
            "alcoholic": self.extract_alcoholic(data),
            "ingredients": self.extract_ingredients(data),
            "glass": self.extract_glass(data),
            "thumbnail": self.extract_thumbnail(data)
        }


    def process(self, cocktail):
        # Full data processing pipeline
        tweet = {}
        tweet["image"] = self.download_thumbnail(cocktail["thumbnail"])
        tweet["ingredients"] = self.introduce_emojis(cocktail["ingredients"])
        instructions = self.modify_instructions(cocktail["instructions"])
        tweet["instructions"] = self.split_instructions(instructions)
        sheet = self.build_main(cocktail["name"], cocktail["alcoholic"], tweet["ingredients"], cocktail["glass"])
        tweet["sheet"] = sheet
        
        return tweet


def write_log(data):
    # Simply write data to a logfile
    with open(LOG_FILE, "a") as logfile:
        logfile.write(data)


def periodic_workflow(max_retries=5):
    # There is a maximum of retries, for safety
    if max_retries < 0:
        write_log("[FAILED] Reached maximum of retries at {}.\n".format(datetime.datetime.now()))
        exit(1)
        
    # Workflow that executes every few hours
    try:
        c = CocktailBot()
        data = c.get_cocktail("random")
        content = c.extract(data)
        tweet = c.process(content)
        c.post_tweet(tweet)
        with open("log.txt", "a") as logfile:
            write_log("[POSTED] Id: {} at {}.\n".format(data["idDrink"], datetime.datetime.now()))
    except Exception as e:
        print(e)
        with open("log.txt", "a") as logfile:
            write_log("[FAILED] Id: {} at {}.\n".format(data["idDrink"], datetime.datetime.now()))
        time.sleep(SLEEP_BETWEEN_RETRIES)
        periodic_workflow(max_retries - 1)


if __name__ == "__main__":
    periodic_workflow()