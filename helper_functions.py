import random
import asyncio
import discord


def shuffle_deck(deck, player_name=None):
    random.shuffle(deck)
    if player_name:
        f"{player_name}'s deck has been shuffled."
    return deck


def determine_first_player(players):
    # Sort players by score, minion count, and treasure count
    sorted_players = sorted(players.items(), key=lambda item: (item[1].score, len(item[1].minions), len(item[1].treasure)))

    # Check if the top players are tied
    top_players = [sorted_players[0]]
    for player in sorted_players[1:]:
        player_ob = player[1]
        top_player = top_players[0][1]
        if (player_ob.score == top_player.score and
                len(player_ob.minions) == len(top_player.minions) and
                len(player_ob.treasure) == len(top_player.treasure)):
            top_players.append(player)
        else:
            break

    # If there's a tie, choose randomly among the top players
    if len(top_players) > 1:
        return random.choice(top_players)

    # Otherwise, return the top player
    return top_players[0]


def roll_dice(die):
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

def get_dice_dict(game_engine, exclude_dice=[], only_char_name=[]):
    if exclude_dice is None:
        exclude_dice = list()
    if exclude_dice is None:
        exclude_dice = []
    dice_dict = {}
    for p_obj in get_all_player_objs(game_engine):
        character_name = p_obj.character.name
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
    for key, dice_info in dice_dict.items():
        prompt_message += f"{key} - {dice_info['die_type']}({dice_info['value']})\n"
    return prompt_message


# For sending public messages
async def send_public_message(game_engine, message):
    await game_engine.ctx.send(message)


# For sending DMs
async def send_dm(game_engine, player_obj, message, need_response=False, double=True):
    discord_id = player_obj.discord_id
    if discord_id != "Bot":
        user = await game_engine.bot.fetch_user(discord_id)
        dm_channel = await user.create_dm()
        await dm_channel.send(message)
    else:
        print("Bot DM:", message)  # Handle bot DMs as needed
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
                print('DM', response)
                if double:
                    selected_character, selected_index = response.content.strip().split()
                    selected_index = int(selected_index) - 1
                    return selected_character, selected_index
                return response.content.strip()
            except asyncio.TimeoutError:
                pass  # Continue the loop if no response yet

        await dm_channel.send("Time's up!")
        return None


# async def send_dm(game_engine, player_obj, message, need_response=False, double=True):
#     discord_id = player_obj.discord_id
#     if discord_id != "Bot":
#         user = await game_engine.bot.fetch_user(discord_id)
#         dm_channel = await user.create_dm()
#         await dm_channel.send(message)
#     else:
#         print("Bot DM:", message)  # Handle bot DMs as needed
#         if need_response:
#             response = await player_obj.make_choice(message)
#             if double:
#                 selected_character, selected_index = response.strip().split()
#                 selected_index = int(selected_index) - 1
#                 return selected_character, selected_index
#             return response.strip()
#
#     if need_response:
#         timeout = 60
#         intervals = [5, 15, 30, 45]
#
#         def check(m):
#             return m.author.id == discord_id and m.channel.type == discord.ChannelType.private
#
#         for remaining in range(timeout, 0, -1):
#             try:
#                 if remaining in intervals:
#                     await dm_channel.send(f"You have {remaining}s left to respond.")
#                 response = await game_engine.bot.wait_for('message', check=check, timeout=1)
#                 print('DM', response)
#                 if double:
#                     selected_character, selected_index = response.content.strip().split()
#                     selected_index = int(selected_index) - 1
#                     return selected_character, selected_index
#                 return response.content.strip()
#             except asyncio.TimeoutError:
#                 await dm_channel.send("Time's up!")
#                 return None


def construct_hand_message(player_obj):
    return "Cards:\n" + "\n".join(
        f"{idx + 1} - {card['name']}, {card['bonuses']}" for idx, card in enumerate(player_obj.hand)
    )


def construct_minion_message(player_obj):
    message = "\n\nMinions:\n"
    message += "\n".join(
        f"{idx + 1 + len(player_obj.hand)} - {minion.name}, {minion.bonus}" for idx, minion in
        enumerate(player_obj.minions)
    )
    if player_obj.used_minions and player_obj.minions:
        message += "\n"
    message += "\n".join(
        f"Used: {minion.name}, {minion.bonus}" for idx, minion in enumerate(player_obj.used_minions)
    )
    return message


def construct_treasure_message(player_obj, final_round):
    message = "\n\nTreasures:\n"
    if final_round:
        message += "\n".join(
            f"{idx + 1 + len(player_obj.hand) + len(player_obj.minions)} - {card['name']}, {card['bonuses']}" for
            idx, card
            in enumerate(player_obj.treasure)
        )
    else:
        message += "\n".join(
            f"{card['name']}, {card['bonuses']}" for idx, card in enumerate(player_obj.treasure)
        )
    return message

