import asyncio
import discord

from characters.minions import minions
from characters.treasures import treasure_deck
from helper_functions import (roll_dice, add_wanda_die, shuffle_deck, send_public_message, send_dm, get_player_obj,
                              get_all_player_objs, get_player_name_by_character, get_dice_dict,
                              create_dice_prompt_message)


class CardHandler:
    def __init__(self, game_engine, player_manager, game_state, bot):
        self.game_engine = game_engine
        self.player_manager = player_manager
        self.game_state = game_state
        self.bot = bot

        self.minions = minions[:-1]  # Exclude the boss minion
        self.minions = shuffle_deck(self.minions)
        self.minions.append(minions[-1])  # Add the boss minion at the bottom

        self.treasures = shuffle_deck(treasure_deck)  # List of treasure cards

    def reset(self):
        self.minions = minions[:-1]  # Exclude the boss minion
        self.minions = shuffle_deck(self.minions)
        self.minions.append(minions[-1])  # Add the boss minion at the bottom
        self.treasures = shuffle_deck(treasure_deck)  # List of treasure cards

    async def play_card(self, player_name, card_number, pass_turn=True):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            await send_public_message(self.game_engine, f"{player_name} is not in the game.")
            return

        response, bonuses, card, is_gold = await self.get_card_details(player_obj, card_number)
        print(is_gold, bonuses)
        if not bonuses:
            return response  # This could be an error message.

        last_card_played = None
        last_player_obj = None
        if "Nope" in bonuses:
            last_player_obj = get_player_obj(self.game_engine, self.game_engine.game_state.last_player)
            if last_player_obj and last_player_obj.cards_in_play:
                last_card_played = last_player_obj.cards_in_play[-1]
                if ("Gold Card" in last_card_played.get('keyword', []) or
                        "Treasure" in last_card_played.get('keyword', [])):
                    await send_public_message(self.game_engine,
                                              f"Cannot 'Nope' a Gold or Treasure card. Choose a different Card")
                    return
            else:
                await send_public_message(self.game_engine, "No card to 'Nope'. Choose a different Card.")
                return

        response += await self.handle_card_bonuses(player_obj, bonuses, is_gold)

        if "Nope" in bonuses:
            player_obj.cards_in_play.append(card)
            if "Defiant Laugh" in last_card_played.get('keyword', []):
                bonuses = await self.handle_jerry_dice(last_player_obj, ["D6"], False)

        await self.finalize_card_play(player_obj, response)
        if pass_turn:
            await self.game_engine.next_turn(player_name)

    async def get_card_details(self, player_obj, card_number):
        player_name = player_obj.name
        num_hand_cards = len(player_obj.hand)
        num_minion_cards = len(player_obj.minions)
        num_treasure_cards = len(player_obj.treasure)
        response = ""
        bonuses = []
        card = ""
        is_gold = False

        if card_number <= num_hand_cards:
            # Regular card play logic for cards in hand
            try:
                card = player_obj.hand.pop(card_number - 1)
                player_obj.cards_in_play.append(card)
                await send_public_message(self.game_engine, f"{player_name} played {card['name']}.")
                bonuses.extend(card.get("bonuses", []))

                if "Gold Card" in card.get('keyword', []):
                    is_gold = True

            except IndexError:
                return "Invalid card number."
        elif num_hand_cards < card_number <= num_hand_cards + num_minion_cards:
            # Use minion bonus
            minion_index = card_number - num_hand_cards - 1
            minion = player_obj.minions[minion_index]
            player_obj.minions.remove(minion)
            player_obj.used_minions.append(minion)
            response += f"{player_name} used {minion.name}'s {minion.bonus}"
            bonuses.extend(minion.bonus)
        elif self.game_engine.is_final_round and num_hand_cards + num_minion_cards < card_number <= num_hand_cards + num_minion_cards + num_treasure_cards:
            treasure_index = card_number - num_hand_cards - num_minion_cards - 1
            treasure = player_obj.treasure.pop(treasure_index)
            player_obj.cards_in_play.append(treasure)
            await send_public_message(self.game_engine, f"{player_name} played {treasure['name']}.")
            bonuses.extend(treasure.get("bonuses", []))
        else:
            return "Invalid card or minion bonus number."

        return response, bonuses, card, is_gold

    async def handle_card_bonuses(self, player_obj, bonuses, is_gold):
        player_name = player_obj.name
        response = ""

        if player_obj.character.name == "Jerry" and any(bonus.startswith("D") for bonus in bonuses):
            bonuses = await self.handle_jerry_dice(player_obj, bonuses, is_gold)

        # Handle bonuses on the card
        for bonus in bonuses:
            if "Nope" in bonus:
                last_player = get_player_obj(self.game_engine, self.game_state.last_player)
                noped_card = last_player.cards_in_play[-1]
                self.game_state.revert_state()
                last_player.discard.append(noped_card)
                response = f"{self.game_state.last_player}'s last card was canceled by 'Nope'."
            elif "Redistribute" in bonus:
                await self.redistribute_dice(player_name)
            elif "Reroll All" in bonus:
                await self.reroll_all_except(player_name)
            elif "Reroll Any" in bonus:
                await self.prompt_reroll(player_name, reroll_any=True)
            elif "Reroll D12" in bonus:
                await self.prompt_reroll(player_name, reroll_any=False, only_D12=True)
            elif "Reroll" in bonus:
                await self.prompt_reroll(player_name, reroll_any=False)
            elif "Upgrade" in bonus:
                await self.prompt_upgrade_die(player_name)
            elif "Reuse Any" in bonus:
                await self.prompt_reuse_ability(player_name, reuse_any=True, is_gold=is_gold)
            elif "Reuse" in bonus:
                await self.prompt_reuse_ability(player_name, reuse_any=False, is_gold=is_gold)
            elif "Swap" in bonus:
                await self.prompt_swap_dice(player_name)
            elif "Die@4" in bonus:
                await self.prompt_set_die_value(player_name, 4)
            elif "D4@2" in bonus:
                player_obj.dice_in_play.extend([("D4", 2)])
                bonus = "D4"
                die_roll = 2
                response += f"\n{player_name} added a {bonus} set to {die_roll}."
            elif bonus.startswith("D") and player_obj.character.name not in ["Jerry"]:
                die_roll = roll_dice(bonus)
                if is_gold:
                    player_obj.gold_dice.extend([(bonus, die_roll)])
                else:
                    player_obj.dice_in_play.extend([(bonus, die_roll)])
                response += f"\n{player_name} rolled {bonus} and got {die_roll}."
                if die_roll == 1 and player_obj.character.name == "Wanda" and bonus not in ["D12"]:
                    response += add_wanda_die(player_obj, bonus)

        return response

    async def finalize_card_play(self, player_obj, response):
        player_name = player_obj.name
        # After playing a card, calculate the new score, record last played, and save state
        self.game_state.last_player = player_name
        for name in self.player_manager.players:
            self.game_state.calculate_score(name)
            self.game_state.save_state(name)

        if "Nope" not in response:
            self.game_engine.consecutive_passes = 0

        task = asyncio.create_task(self.game_engine.player_manager.display_hand(player_name))

        if response:
            await send_public_message(self.game_engine, response)
        return

    async def prompt_reroll(self, player_name, reroll_any, only_D12=False):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            await send_dm(self.game_engine, player_obj, "No player. dice reroll")
            return

        # Generate the list of dice with character names
        dice_dict = {}
        if only_D12:
            dice_dict = get_dice_dict(self.game_engine, only_char_name=player_obj.character.name, get_gold=True,
                                      exclude_dice=["D4", "D6", "D8"])
        else:
            dice_dict = get_dice_dict(self.game_engine, only_char_name=player_obj.character.name, get_gold=True)
            if reroll_any:
                dice_dict.update(get_dice_dict(self.game_engine, exclude_char_name=player_name))

        prompt_message = create_dice_prompt_message(dice_dict, "Reroll")
        selected_character, selected_index = await send_dm(self.game_engine, player_obj, prompt_message,
                                                           need_response=True)
        # Translate character name back to player name
        if selected_index == "NA":
            await send_public_message(self.game_engine, f"\n{player_name} declined the reroll.")
            return
        selected_player_name = get_player_name_by_character(self.game_engine, selected_character)
        rerolled, new_roll, old_roll = self.reroll_die(selected_player_name, selected_index)
        await send_public_message(self.game_engine,
                                  f"\n{player_name} rerolled {selected_character}'s {rerolled}({old_roll}) and got {new_roll}.")

    def reroll_die(self, player_name, die_index):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            return f"{player_name} is not in the game."

        # Retrieve the die to reroll
        num_dice = len(player_obj.dice_in_play)
        num_gold = len(player_obj.gold_dice)
        if die_index + 1 <= num_dice:
            die_to_reroll = player_obj.dice_in_play[die_index]
        elif num_dice < die_index + 1 <= num_dice + num_gold:
            die_to_reroll = player_obj.gold_dice[die_index - num_dice]
        else:
            print('invalid die number')
            return "Invalid die number."

        # Perform the reroll
        print('rerolling dice', die_to_reroll[0], die_to_reroll[1])
        new_roll = roll_dice(die_to_reroll[0])  # Rerolling the same type of die
        print('got', new_roll)
        if die_index + 1 <= num_dice:
            player_obj.dice_in_play[die_index] = (die_to_reroll[0], new_roll)
        elif num_dice < die_index + 1 <= num_dice + num_gold:
            player_obj.gold_dice[die_index - num_dice] = (die_to_reroll[0], new_roll)

        return die_to_reroll[0], new_roll, die_to_reroll[1]

    async def reroll_all_except(self, exclude_player_name):
        player_obj = get_player_obj(self.game_engine, exclude_player_name)
        # Step 1: List all dice except for the specified player
        dice_dict = get_dice_dict(self.game_engine, exclude_char_name=player_obj.character.name)

        # Step 2: Prompt for confirmation
        if not dice_dict:
            await send_public_message(self.game_engine, "No dice available to reroll.")
            return
        prompt_message = f"Do you want to reroll all these dice?: (yes, no)\n"
        for key, dice_info in dice_dict.items():
            prompt_message += f"{key} - {dice_info['die_type']}({dice_info['value']})\n"

        # Replace 'your_discord_id' with the ID of the person who needs to confirm
        confirmation = await send_dm(self.game_engine, player_obj, prompt_message, need_response=True, double=False)

        # Step 3: If confirmed, reroll the dice
        if confirmation.lower() == 'yes':
            for key, dice_info in dice_dict.items():
                new_value = roll_dice(
                    dice_info['die_type'])  # Assuming roll_dice function returns a new value for the die
                rr_player_name = get_player_name_by_character(self.game_engine, dice_info["character"])
                rr_play_obj = get_player_obj(self.game_engine, rr_player_name)
                rr_play_obj.dice_in_play[dice_info["index"]] = (dice_info["die_type"], new_value)
                await send_public_message(self.game_engine,
                                          f"{dice_info['character']}'s {dice_info['die_type']} rerolled to {new_value}.")
        else:
            await send_public_message(self.game_engine, "Reroll cancelled.")

    async def prompt_upgrade_die(self, player_name):
        player_obj = get_player_obj(self.game_engine, player_name)
        # Generate a list of upgradeable dice (D4 and D6)
        dice_dict = get_dice_dict(self.game_engine, exclude_dice=["D12", "D8"])

        if not dice_dict:
            await send_dm(self.game_engine, player_obj.discord_id, "No dice available to upgrade.")
            return

        prompt_message = create_dice_prompt_message(dice_dict, "Upgrade")
        selected_character, selected_index = await send_dm(self.game_engine, player_obj, prompt_message,
                                                           need_response=True)

        if selected_index == "NA":
            await send_public_message(self.game_engine, f"\n{player_name} declined the Upgrade.")
            return
        # Find the player and upgrade the die
        selected_player_name = get_player_name_by_character(self.game_engine, selected_character)
        die_upgraded, new_value = self.upgrade_die(selected_player_name, selected_index)
        response = f"\n{player_name} upgraded {selected_character}'s {die_upgraded[0]} to D8 with a new value of {new_value}"
        await send_public_message(self.game_engine, response)

    def upgrade_die(self, player_name, die_index):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            return f"{player_name} is not in the game."

        if die_index[0] in ["D4", "D6"]:
            # Upgrade to D8 and increase value by 2
            player_obj.dice_in_play[die_index] = ("D8", min(die_index[1] + 2, 8))
            return die_index[1], min(die_index[1] + 2, 8)

    async def prompt_set_die_value(self, player_name, set_value):
        player_obj = get_player_obj(self.game_engine, player_name)
        # Logic to list all dice
        dice_dict = get_dice_dict(self.game_engine)

        prompt_message = create_dice_prompt_message(dice_dict, f"Set to {set_value}")
        selected_character, selected_index = await send_dm(self.game_engine, player_obj, prompt_message,
                                                           need_response=True)

        if selected_index == "NA":
            await send_public_message(self.game_engine, f"\n{player_name} declined the Set Die.")
            return

        # Find the player and set the die's value
        selected_player_name = get_player_name_by_character(self.game_engine, selected_character)
        die_set, new_value = self.set_die(selected_player_name, selected_index, set_value)
        response = f"\n{player_name} set {selected_character}'s {die_set} to {new_value}."
        await send_public_message(self.game_engine, response)

    def set_die(self, player_name, die_index, set_value):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            return f"{player_name} is not in the game."

        player_obj.dice_in_play[die_index] = (player_obj.dice_in_play[die_index][0], set_value)

        return player_obj.dice_in_play[die_index][0], set_value

    async def prompt_reuse_ability(self, player_name, reuse_any=False, is_gold=False):
        player_obj = get_player_obj(self.game_engine, player_name)
        discarded_item_cards = {}
        if reuse_any:
            # Step 1: Gather Discarded Item Cards
            for p_obj in get_all_player_objs(self.game_engine):
                for idx, card in enumerate(p_obj.discard):
                    if 'Item' in card.get('keyword', []):
                        card_key = f"{p_obj.character.name} {idx + 1}"
                        discarded_item_cards[card_key] = {"name": card["name"],
                                                          "bonuses": card["bonuses"],
                                                          }
        else:
            for idx, card in enumerate(player_obj.discard):
                if 'Item' in card.get('keyword', []):
                    card_key = f"{player_obj.character.name} {idx + 1}"
                    discarded_item_cards[card_key] = {"name": card["name"],
                                                      "bonuses": card["bonuses"],
                                                      }

        # Check if there are any item cards available
        if not discarded_item_cards:
            # Send a message if no item cards are available
            await send_dm(self.game_engine, player_obj, "No 'Item' cards in discard to reuse.")
            return None

        prompt_message = "Choose an 'Item' card to Reuse (format: CharacterName DieNumber):\n"
        for key, card_info in discarded_item_cards.items():
            prompt_message += f"{key} - {card_info['name']} {card_info['bonuses']}\n"

        selected_character, selected_index = await send_dm(self.game_engine, player_obj, prompt_message,
                                                           need_response=True)
        selected_player_name = get_player_name_by_character(self.game_engine, selected_character)
        selected_player_obj = get_player_obj(self.game_engine, selected_player_name)

        # now pop that card out of discard, and play it
        reused_card = selected_player_obj.discard[selected_index]
        if is_gold and 'Gold Card' not in reused_card['keyword']:
            reused_card['keyword'].append('Gold Card')
        player_obj.hand.append(selected_player_obj.discard[selected_index])
        selected_player_obj.discard.pop(selected_index)
        await self.play_card(player_name, len(player_obj.hand), pass_turn=False)

    async def prompt_swap_dice(self, player_name):
        player_obj = get_player_obj(self.game_engine, player_name)
        # List all dice from all players except the requesting player
        dice_dict = get_dice_dict(self.game_engine)

        # Prompt for the first die to swap
        first_die_key = await self.prompt_for_die_selection(player_obj, dice_dict, "Choose the first die to swap:")
        if not first_die_key:
            return "No selection made for the first die."
        first_die_info = dice_dict[first_die_key]

        for key in list(dice_dict.keys()):
            if first_die_info['character'] in key:
                del dice_dict[key]

        # Prompt for the second die to swap
        second_die_key = await self.prompt_for_die_selection(player_obj, dice_dict,
                                                             "Choose the second die to swap:")
        if not second_die_key:
            return "No selection made for the second die."
        second_die_info = dice_dict[second_die_key]
        # Perform the swap
        print(first_die_info)
        print(second_die_info)
        await self.swap_dice(first_die_info, second_die_info)

    async def prompt_for_die_selection(self, player_obj, dice_dict, prompt_message):
        # Create a message listing the dice for the player to choose from
        dice_list_message = "\n".join([f"{key}: {info['die_type']}({info['value']})" for key, info in dice_dict.items()])
        full_message = prompt_message + "\n" + dice_list_message
        die_key = await send_dm(self.game_engine, player_obj, full_message, need_response=True, double=False)
        return die_key

    async def swap_dice(self, first_die_info, second_die_info):
        # Retrieve the player objects
        first_char_name = first_die_info['character']
        first_play_name = get_player_name_by_character(self.game_engine, first_char_name)
        first_play_obj = get_player_obj(self.game_engine, first_play_name)
        second_char_name = second_die_info['character']
        second_play_name = get_player_name_by_character(self.game_engine, second_char_name)
        second_play_obj = get_player_obj(self.game_engine, second_play_name)

        # Swap the dice
        (first_play_obj.dice_in_play[first_die_info['index']],
         second_play_obj.dice_in_play[second_die_info['index']]) = \
            (second_play_obj.dice_in_play[second_die_info['index']],
             first_play_obj.dice_in_play[first_die_info['index']])

        message = (f"Swapped {first_die_info['character']}'s {first_die_info['die_type']}({first_die_info['value']} and"
                   f" {second_die_info['character']}'s {second_die_info['die_type']}({second_die_info['value']}.")

    async def redistribute_dice(self, player_name):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            await send_dm(self.game_engine, player_obj, "You are not in the game.")
            return

        # Collect available dice from all players and create a dictionary
        dice_dict = get_dice_dict(self.game_engine)
        char_grouped_names = ""
        # Group dice by character
        dice_by_character = {}
        for dice_key, dice_info in dice_dict.items():
            char_name = dice_info['character']
            if char_name not in char_grouped_names:
                char_grouped_names += char_name + ", "
            if char_name not in dice_by_character:
                dice_by_character[char_name] = []
            dice_by_character[char_name].append((dice_key, dice_info))

        char_grouped_names = char_grouped_names.rstrip(", ")

        # Prompt the player to select one die from each character
        selected_dice = {}
        for char_name, char_dice in dice_by_character.items():
            prompt_message = f"Select a die from {char_name}:\n" + "\n".join(
                f"{dice_key} - {dice_info['die_type']}({dice_info['value']})" for dice_key, dice_info in char_dice
            )
            selected_dice_key = await send_dm(self.game_engine, player_obj, prompt_message, need_response=True,
                                              double=False)
            selected_dice[selected_dice_key] = dice_dict[selected_dice_key]

            # Remove the selected die from the original character
            play_name_from_char = get_player_name_by_character(self.game_engine, char_name)
            original_player_obj = get_player_obj(self.game_engine, play_name_from_char)
            dice_index = dice_dict[selected_dice_key]['index']
            original_player_obj.dice_in_play.pop(dice_index)

        # Prompt the player to redistribute the selected dice
        for dice_key, dice_info in selected_dice.items():
            prompt_message = f"Assign {dice_info['character']}'s {dice_info['die_type']}({dice_info['value']}) to which character? ({char_grouped_names})"
            new_owner_char_name = await send_dm(self.game_engine, player_obj, prompt_message, need_response=True,
                                                double=False)
            new_owner_player = get_player_name_by_character(self.game_engine, new_owner_char_name)
            new_owner_player_obj = get_player_obj(self.game_engine, new_owner_player)
            new_owner_player_obj.dice_in_play.append((dice_info['die_type'], dice_info['value']))

    async def handle_jerry_dice(self, player_obj, bonuses, is_gold):
        dice_list = []
        for bonus in bonuses:
            if bonus.startswith("D"):
                dice_list.append(bonus)
        for die in dice_list:
            bonuses.remove(die)
        dice_list.append("D6")
        rolled_dice = []
        for die in dice_list:
            die_roll = roll_dice(die)
            print('jerry die roll', die_roll, die)
            rolled_dice.extend([(die, die_roll)])
        # List the dice for the player to choose which to discard
        dice_list_msg = "Choose a die to discard:\n" + "\n".join(
            [f"{idx + 1} - {die}({value})" for idx, (die, value) in enumerate(rolled_dice)]
        )
        selected_index = await send_dm(self.game_engine, player_obj, dice_list_msg, need_response=True, double=False)
        selected_index = int(selected_index) - 1
        if 0 <= selected_index < len(rolled_dice):
            discarded_die = rolled_dice.pop(selected_index)
            for die in rolled_dice:
                if is_gold:
                    player_obj.gold_dice.append(die)
                else:
                    player_obj.dice_in_play.append(die)
            await send_dm(self.game_engine, player_obj, f"You discarded {discarded_die}.")
        else:
            await send_dm(self.game_engine, player_obj, "Invalid selection.")

        return bonuses


