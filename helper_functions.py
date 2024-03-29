import random
import asyncio
import time

import discord
from fuzzywuzzy import process


def shuffle_deck(deck, player_name=None):
    random.shuffle(deck)
    if player_name:
        f"{player_name}'s deck has been shuffled."
    return deck


def roll_dice(die):
    time.sleep(.05)
    if die == "D4":
        return random.randint(1, 4)
    elif die == "D6":
        return random.randint(1, 6)
    elif die == "D8":
        return random.randint(1, 8)
    elif die == "D12":
        return random.randint(1, 12)


def add_wanda_die(player_obj, die):
    die_roll = roll_dice(die)
    player_obj.dice_in_play.extend([(die, die_roll)])
    return f"\nWanda's {die} exploded and got a {die_roll}!"


def get_player_obj(game_engine, player_name):
    return game_engine.player_manager.players.get(player_name)


def get_all_player_objs(game_engine):
    player_objs = [game_engine.player_manager.players.get(player_name) for player_name in
                   game_engine.player_manager.players]

    # Sort the list so that "Jerry" comes last
    player_objs = sorted(player_objs, key=lambda player: player.character.name == "Jerry")

    return player_objs


def get_player_name_by_character(game_engine, character_name):
    for player_obj in get_all_player_objs(game_engine):
        if player_obj.character.name.lower() == character_name.lower():
            return player_obj.name
    return None


def determine_lead(player_objs, me):
    player_scores = [player.score for player in player_objs if player is not me]
    difference = [score - me.score for score in player_scores]
    if difference:
        return max(difference)
    return -1


# def get_list_dice(game_engine, exclude_dice=[]):
#     dice_list = []
#     for p_obj in get_all_player_objs(game_engine):
#         character_name = p_obj.character.name
#         for idx, (die, value) in enumerate(p_obj.dice_in_play):
#             if exclude_dice:
#                 if die not in exclude_dice:
#                     dice_list.append(f"{character_name} {idx + 1} - {die}({value})")
#             else:
#                 dice_list.append(f"{character_name} {idx + 1} - {die}({value})")
#
#     return dice_list

def get_dice_dict(game_engine, exclude_dice=[], only_char_name=[], exclude_char_name=None, get_gold=False):
    dice_dict = {}
    for p_obj in get_all_player_objs(game_engine):
        character_name = p_obj.character.name
        print('car names', character_name, only_char_name)
        if character_name != exclude_char_name:
            if not only_char_name or character_name in only_char_name:
                for idx, (die, value) in enumerate(p_obj.dice_in_play):
                    if not exclude_dice or die not in exclude_dice:
                        dice_key = f"{character_name} {idx + 1}"
                        from_av = 0
                        if die == "D4":
                            from_av = value - 2.5
                        elif die == "D6":
                            from_av = value - 3.5
                        elif die == "D8":
                            from_av = value - 4.5

                        dice_dict[dice_key] = {
                            "index": idx,
                            "character": character_name,
                            "die_type": die,
                            "value": value,
                            "from_average": from_av,
                        }

                if get_gold:
                    print('is gold')
                    for idx, (die, value) in enumerate(p_obj.gold_dice):
                        if not exclude_dice or die not in exclude_dice:
                            dice_key = f"{character_name} {len(p_obj.dice_in_play) + idx + 1}"
                            from_av = 0
                            if die == "D4":
                                from_av = value - 2.5
                            elif die == "D6":
                                from_av = value - 3.5
                            elif die == "D8":
                                from_av = value - 4.5
                            elif die == "D12":
                                from_av = value - 6.5

                            dice_dict[dice_key] = {
                                "index": idx,
                                "character": character_name,
                                "die_type": die,
                                "value": value,
                                "from_average": from_av,
                            }
    return dice_dict


def create_dice_prompt_message(dice_dict, bonus):
    prompt_message = f"Choose a die to {bonus} (format: CharacterName DieNumber):\n"
    user_choices = []
    for key, dice_info in dice_dict.items():
        prompt_message += f"{key} - {dice_info['die_type']}({dice_info['value']})\n"
        user_choices.append(key)
    prompt_message += f"NA NA - For None\n"
    user_choices.append("NA NA")
    print('user_choices', user_choices)
    return prompt_message, user_choices


# For sending public messages
async def send_public_message(game_engine, message):
    await game_engine.ctx.send(message)


# For sending DMs
async def send_dm(game_engine, player_obj, message, user_choices=[], need_response=False, double=True):
    discord_id = player_obj.discord_id
    if discord_id != "Bot":
        user = await game_engine.bot.fetch_user(discord_id)
        dm_channel = await user.create_dm()
        await dm_channel.send(message)
    else:
        # print("Bot DM:", message)  # Handle bot DMs as needed
        if need_response:
            response = await player_obj.make_choice(message)
            if double:
                await asyncio.sleep(2)
                selected_character, selected_index = response.strip().split()
                selected_index = int(selected_index) - 1
                return selected_character, selected_index
            return response.strip()

    if need_response:
        timeout = 60
        intervals = [45, 30, 15, 5]
        start_time = game_engine.bot.loop.time()

        def check(m):
            return m.author.id == discord_id and m.channel.type == discord.ChannelType.private

        while True:
            try:
                elapsed = game_engine.bot.loop.time() - start_time
                remaining = timeout - elapsed
                if remaining <= 0:
                    break  # Timeout reached

                if int(remaining) in intervals:
                    await dm_channel.send(f"You have {int(remaining)}s left to respond.")

                response = await game_engine.bot.wait_for('message', check=check, timeout=1)
                response = response.content.strip()
                if user_choices:
                    response = clean_input(response, user_choices)
                if double:
                    selected_character, selected_index = response.split()
                    if selected_character == "NA":
                        return selected_character, selected_index
                    selected_index = int(selected_index) - 1
                    return selected_character, selected_index
                return response.content.strip()
            except asyncio.TimeoutError:
                pass  # Continue the loop if no response yet

        await dm_channel.send("Time's up!")
        return None


def clean_input(user_input, user_choices):
    closest_match, score = process.extractOne(user_input, user_choices)
    # You might want to check the score here to see if it's high enough to be considered a match.
    # For example, you could only accept matches where the score is above 80.
    # if score > 74:
    print('closest match', closest_match, score)
    return closest_match
    # else:
    #     return None
