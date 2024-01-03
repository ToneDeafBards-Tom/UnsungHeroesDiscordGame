import discord
from discord.ext import commands
from game_engine import GameEngine
from characters.alfred import Alfred

intents = discord.Intents.all()
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)
characters = {"Alfred": Alfred}
game_engine = GameEngine(characters, bot)

# Read the bot token from the config.txt file
with open("config.txt", "r") as file:
    BOT_TOKEN = file.read().strip()


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')


@bot.command(name="choose_character")
async def choose_character(ctx, character_name):
    player_name = ctx.author.name
    response = game_engine.choose_character(player_name, character_name)
    await ctx.send(response)


@bot.command(name="shuffle_deck")
async def shuffle_deck(ctx):
    player_name = ctx.author.name
    response = game_engine.shuffle_deck(player_name)
    await ctx.send(response)


@bot.command(name="draw_cards")
async def draw_cards(ctx):
    player_name = ctx.author.name
    response = game_engine.draw_cards(player_name)
    await ctx.send(response)


@bot.command(name="display_hand")
async def display_hand(ctx):
    player_name = ctx.author.name
    player_id = ctx.author.id
    player_dm = await ctx.author.create_dm()

    response = game_engine.display_hand(player_name)
    await player_dm.send(response)


@bot.command(name="join_game")
async def join_game(ctx, character_name: str):
    player_name = ctx.author.name
    discord_id = ctx.author.id
    # Normalize the character name for case-insensitivity
    character_name = character_name.lower().capitalize()
    join_response = game_engine.add_player(player_name, discord_id)
    choose_response = game_engine.choose_character(player_name, character_name)
    await ctx.send(join_response + "\n" + choose_response)


@bot.command(name="start_game")
async def start_game(ctx):
    start_response = await game_engine.start_game(ctx)
    game_state = game_engine.display_game_state()
    await ctx.send(game_state)


@bot.command(name="play_card")
async def play_card_command(ctx, card_number: int):
    player_name = ctx.author.name
    response = await game_engine.play_card(player_name, card_number)
    await ctx.send(response)
    await game_engine.display_hand(player_name)
    await game_state_command(ctx)


@bot.command(name="game_state")
async def game_state_command(ctx):
    response = game_engine.display_game_state()
    await ctx.send(response)


@bot.command(name="end_round")
async def end_round_command(ctx):
    round_winner = game_engine.determine_winner()
    await ctx.send(f"Round winner: {round_winner.name}! See DM for Treasure selection.")
    await game_engine.draw_treasures(round_winner)
    game_engine.prepare_next_round()
    round_start = await game_engine.start_round()
    if game_engine.is_final_round:
        await ctx.send("***The final round has begun! The boss card is drawn.***")
    game_state = game_engine.display_game_state()
    await ctx.send(game_state)


@bot.command(name="restart_game")
async def restart_game_command(ctx):
    game_engine.restart_game()
    await ctx.send("Game has been reset. Rejoin to play again")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
