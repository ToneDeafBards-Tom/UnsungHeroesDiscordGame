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


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')

#
# @bot.command(name="choose_character")
# async def choose_character(ctx, character_name):
#     player_name = ctx.author.name
#     response = game_engine.choose_character(player_name, character_name)
#     await ctx.send(response)
#
#
# @bot.command(name="shuffle_deck")
# async def shuffle_deck(ctx):
#     player_name = ctx.author.name
#     response = game_engine.player_manager.shuffle_deck(player_name)
#     await ctx.send(response)
#
#
# @bot.command(name="draw_cards")
# async def draw_cards(ctx):
#     player_name = ctx.author.name
#     response = game_engine.player_manager.draw_cards(player_name)
#     await ctx.send(response)
#
#
# @bot.command(name="display_hand")
# async def display_hand(ctx):
#     player_name = ctx.author.name
#     player_id = ctx.author.id
#     player_dm = await ctx.author.create_dm()
#
#     response = game_engine.player_manager.display_hand(player_name)
#     await player_dm.send(response)


@bot.command(name="join_game")
async def join_game(ctx, character_name: str):
    player_name = ctx.author.name
    discord_id = ctx.author.id
    # Normalize the character name for case-insensitivity
    character_name = character_name.lower().capitalize()
    join_response = game_engine.player_manager.add_player(player_name, discord_id)
    choose_response = game_engine.player_manager.choose_character(player_name, character_name)
    await ctx.send(join_response + "\n" + choose_response)

@bot.command(name="add_bot")
async def add_bot_command(ctx, character_name: str):
    if character_name not in characters:  # Assuming 'characters' is your available characters dictionary
        await ctx.send(f"Character '{character_name}' does not exist.")
        return

    if game_engine.game_started:  # Assuming there is a flag in your game engine to check if the game has started
        await ctx.send("Cannot add AI bots after the game has started.")
        return

    ai_bot = AIBot("AI_" + character_name, character_name, "Bot", game_engine)  # Create an AI bot instance
    response = game_engine.player_manager.add_ai_player(ai_bot)  # Add the AI bot to the game engine
    await ctx.send(response)


@bot.command(name="start_game")
async def start_game(ctx):
    start_response = await game_engine.start_game(ctx)
    game_state = game_engine.game_state.display_game_state()
    await ctx.send(game_state)


@bot.command(name="play_card")
async def play_card_command(ctx, card_number: int):
    player_name = ctx.author.name
    response = await game_engine.card_handler.play_card(player_name, card_number, ctx)
    # await ctx.send(response)
    await game_engine.player_manager.display_hand(player_name)
    if "Nope" not in response:
        await game_engine.next_turn(ctx, player_name)
    await game_state_command(ctx)

@bot.command(name="game_state")
async def game_state_command(ctx):
    response = game_engine.game_state.display_game_state()
    await ctx.send(response)


@bot.command(name="end_round")
async def end_round_command(ctx):
    await game_engine.end_round(ctx)


@bot.command(name="restart_game")
async def restart_game_command(ctx):
    game_engine.restart_game()
    await ctx.send("Game has been reset. Rejoin to play again")


@bot.command(name="pass")
async def pass_command(ctx):
    player_name = ctx.author.name
    await game_engine.next_turn(ctx, player_name)



if __name__ == "__main__":
    bot.run(BOT_TOKEN)
