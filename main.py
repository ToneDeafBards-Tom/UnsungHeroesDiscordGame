import discord
from discord.ext import commands
from game_engine import GameEngine
from ai_bot import AIBot
from player_manager import characters


intents = discord.Intents.all()
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)
game_engine = GameEngine(bot)

# Read the bot token from the config.txt file
with open("config.txt", "r") as file:
    BOT_TOKEN = file.read().strip()


# Define the GameManager class
class GameManager:
    def __init__(self):
        self.games = {}  # Dictionary to store games with their unique ID

    def get_game(self, group_id):
        if group_id not in self.games:
            self.games[group_id] = GameEngine(bot)  # Create a new GameEngine instance for the group
        return self.games[group_id]

    def end_game(self, group_id):
        if group_id in self.games:
            del self.games[group_id]


# Instantiate the GameManager globally
game_manager = GameManager()


# Define bot commands
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

@bot.command(name="join_game")
async def join_game(ctx, character_name: str):
    group_id = ctx.channel.id  # Get the unique identifier for the group
    game_engine = game_manager.get_game(group_id)  # Retrieve the game instance for this group
    game_engine.update_ctx(ctx)
    player_name = ctx.author.name
    discord_id = ctx.author.id
    character_name = character_name.lower().capitalize()
    await game_engine.player_manager.add_player(player_name, discord_id, character_name)


@bot.command(name="add_bot")
async def add_bot_command(ctx, character_name: str):
    group_id = ctx.channel.id  # Get the unique identifier for the group
    game_engine = game_manager.get_game(group_id)  # Retrieve the game instance for this group
    if character_name not in characters:  # Assuming 'characters' is your available characters dictionary
        await ctx.send(f"Character '{character_name}' does not exist.")
        return

    if game_engine.game_started:  # Assuming there is a flag in your game engine to check if the game has started
        await ctx.send("Cannot add AI bots after the game has started.")
        return

    game_engine.update_ctx(ctx)
    await game_engine.player_manager.add_player("AI_" + character_name, "Bot", character_name)


@bot.command(name="start_game")
async def start_game(ctx):
    group_id = ctx.channel.id  # Get the unique identifier for the group
    game_engine = game_manager.get_game(group_id)  # Retrieve the game instance for this group
    game_engine.update_ctx(ctx)
    await game_engine.start_game()



@bot.command(name="play_card")
async def play_card_command(ctx, card_number: int):
    group_id = ctx.channel.id  # Get the unique identifier for the group
    game_engine = game_manager.get_game(group_id)  # Retrieve the game instance for this group
    game_engine.update_ctx(ctx)
    player_name = ctx.author.name
    await game_engine.card_handler.play_card(player_name, card_number)
    # # await ctx.send(response)
    # await game_engine.player_manager.display_hand(player_name)
    # if "Nope" not in response:
    #     await game_engine.next_turn(ctx, player_name)


@bot.command(name="game_state")
async def game_state_command(ctx):
    group_id = ctx.channel.id  # Get the unique identifier for the group
    game_engine = game_manager.get_game(group_id)  # Retrieve the game instance for this group
    game_engine.update_ctx(ctx)
    game_engine.game_state.display_game_state()



@bot.command(name="end_round")
async def end_round_command(ctx):
    group_id = ctx.channel.id  # Get the unique identifier for the group
    game_engine = game_manager.get_game(group_id)  # Retrieve the game instance for this group
    game_engine.update_ctx(ctx)
    await game_engine.end_round()


@bot.command(name="restart_game")
async def restart_game_command(ctx):
    group_id = ctx.channel.id  # Get the unique identifier for the group
    game_engine = game_manager.get_game(group_id)  # Retrieve the game instance for this group
    game_engine.update_ctx(ctx)
    game_engine.restart_game()
    await ctx.send("Game has been reset. Rejoin to play again")


@bot.command(name="pass")
async def pass_command(ctx):
    group_id = ctx.channel.id  # Get the unique identifier for the group
    game_engine = game_manager.get_game(group_id)  # Retrieve the game instance for this group
    game_engine.update_ctx(ctx)
    player_name = ctx.author.name
    await game_engine.next_turn(player_name)



if __name__ == "__main__":
    bot.run(BOT_TOKEN)
