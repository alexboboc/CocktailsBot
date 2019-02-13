# :tropical_drink: Cocktails Bot

This repository contains the code behind [@CocktailsBot](https://twitter.com/CocktailsBot), a Twitter bot that **posts a beautifully formatted cocktail recipe every few hours**.

The bot pulls data from the open source API [TheCocktailDB](https://www.thecocktaildb.com/) and employs a hand-made emoji map to display the ingredients in a graphical way.

## Features

In its first version, released back in September 2018, the bot only had one functionality: publishing a cocktail recipe when triggered. The main tweet was the list of ingredients, and the following replies included instructions on how to make it.

As the second version has been released in February 2019, **the bot now has interactive functionalities** and it's capable of answering to user requests. More specifically, the bot supports the two following queries:

- *Make me something with `<ingredient>`.*
- *Make me a/an `<cocktail>`.*

## Structure

- `CocktailBot.py`: pulls, formats and posts cocktails. *Needs access to the Twitter API.*
- `CocktailBotInteractive.py` listens, parses, interprets and responds user queries (mentions), and it's a subclass of `CocktailBot`. *Needs access to a MongoDB database to store processed queries.*
- `emojis.py`: map of ingredients to unicode representations of emojis.
- `setup.py`: simple script ensuring that requirements (folders, packages...) are met.

## References

 I wrote a couple of blog posts explaining the logic behind [@CocktailsBot](https://twitter.com/CocktailsBot):

- [*Implementing a bot that tweets beautifully formatted cocktail recipes*](http://blog.alexboboc.com/implementing-a-bot-that-tweets-beautifully-formatted-cocktail-recipes/)
- [*Extending @CocktailsBot with interactive commands*](https://blog.alexboboc.com/extending-@cocktailsbot-with-interactive-commands)