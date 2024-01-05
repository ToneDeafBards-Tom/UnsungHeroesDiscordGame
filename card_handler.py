import asyncio
import discord

from characters.minions import minions
from characters.treasures import treasure_deck
from helper_functions import (roll_dice, add_wanda_die, shuffle_deck, send_public_message, send_dm, get_player_obj,
                              get_all_player_objs, get_player_name_by_character, get_list_dice)


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

    async def play_card(self, player_name, card_number):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            await send_public_message(self.game_engine, f"{player_name} is not in the game.")
            return

        response, bonuses, card = await self.get_card_details(player_obj, card_number)
        print(bonuses)
        if not bonuses:
            return response  # This could be an error message.

        if "Nope" in bonuses:
            player_obj.cards_in_play.append(card)

        response += await self.handle_card_bonuses(player_obj, bonuses)
        await self.finalize_card_play(player_obj, response)

    async def get_card_details(self, player_obj, card_number):
        player_name = player_obj.name
        num_hand_cards = len(player_obj.hand)
        num_minion_cards = len(player_obj.minions)
        num_treasure_cards = len(player_obj.treasure)
        response = ""
        bonuses = []
        card = ""

        if card_number <= num_hand_cards:
            # Regular card play logic for cards in hand
            try:
                card = player_obj.hand.pop(card_number - 1)
                player_obj.cards_in_play.append(card)
                response += f"{player_name} played {card['name']}."
                bonuses.extend(card.get("bonuses", []))
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
            response += f"{player_name} played {treasure['name']}."
            bonuses.extend(treasure.get("bonuses", []))
        else:
            return "Invalid card or minion bonus number."

        return response, bonuses, card

    async def handle_card_bonuses(self, player_obj, bonuses):
        player_name = player_obj.name
        response = ""

        if player_obj.character.name == "Jerry" and any(bonus.startswith("D") for bonus in bonuses):
            bonuses = await self.handle_jerry_dice(player_obj, bonuses)

        # Handle bonuses on the card
        for bonus in bonuses:
            if "Nope" in bonus:
                last_player = self.player_manager.players.get(self.game_state.last_player)
                noped_card = last_player.cards_in_play[-1]
                self.game_state.revert_state()
                last_player.discard.append(noped_card)
                response = f"{self.game_state.last_player}'s last card was canceled by 'Nope'."

            elif "Reroll Any" in bonus:
                await self.prompt_reroll(player_name, reroll_any=True)
            elif "Reroll" in bonus:
                await self.prompt_reroll(player_name, reroll_any=False)
            elif "Upgrade" in bonus:
                await self.prompt_upgrade_die(player_name)
            elif "Die@4" in bonus:
                await self.prompt_set_die_value(player_name, 4)
            elif "D4@2" in bonus:
                player_obj.dice_in_play.extend([("D4", 2)])
                bonus = "D4"
                die_roll = 2
                response += f"\n{player_name} added a {bonus} set to {die_roll}."
            elif bonus.startswith("D") and player_obj.character.name not in ["Jerry"]:
                die_roll = roll_dice(bonus)
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

        await send_public_message(self.game_engine, response)
        return

    async def prompt_reroll(self, player_name, reroll_any):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            await send_dm(self.game_engine, player_obj, "No player. dice reroll")
            return

        # Generate the list of dice with character names
        dice_list = []
        if reroll_any:
            dice_list = get_list_dice(self.game_engine)
        else:
            # List only the requesting player's dice
            character_name = player_obj.character.name
            for idx, (die, value) in enumerate(player_obj.dice_in_play):
                dice_list.append(f"{character_name} {idx + 1} - {die}({value})")

        prompt_message = "Choose a die to reroll (format: CharacterName DieNumber):\n" + "\n".join(dice_list)
        selected_character, selected_index = await send_dm(self.game_engine, player_obj, prompt_message, need_response=True)
        # Translate character name back to player name
        selected_player_name = get_player_name_by_character(self.game_engine, selected_character)
        rerolled, new_roll = self.reroll_die(selected_player_name, selected_index)
        await send_public_message(self.game_engine, f"\n{player_name} rerolled {selected_character}'s {rerolled} and got {new_roll}.")

    def reroll_die(self, player_name, die_index):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            return f"{player_name} is not in the game."

        try:
            # Retrieve the die to reroll
            die_to_reroll = player_obj.dice_in_play[die_index]
            # Perform the reroll
            new_roll = roll_dice(die_to_reroll[0])  # Rerolling the same type of die
            player_obj.dice_in_play[die_index] = (die_to_reroll[0], new_roll)

            return die_to_reroll[0], new_roll
        except IndexError:
            return "\nInvalid die index."

    async def prompt_upgrade_die(self, player_name):
        player_obj = get_player_obj(self.game_engine, player_name)
        # Generate a list of upgradeable dice (D4 and D6)
        upgradeable_dice = get_list_dice(self.game_engine, exclude_dice=["D12", "D8"])

        if not upgradeable_dice:
            await send_dm(self.game_engine, player_obj.discord_id, "No dice available to upgrade.")
            return

        prompt_message = "Choose a die to upgrade (D4 or D6, format: CharacterName DieNumber):\n" + "\n".join(
            upgradeable_dice)
        selected_character, selected_index = await send_dm(self.game_engine, player_obj, prompt_message, need_response=True)

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
        dice_list = get_list_dice(self.game_engine)

        prompt_message = "Choose a die to set to value " + str(
            set_value) + " (format: CharacterName DieNumber):\n" + "\n".join(dice_list)
        selected_character, selected_index = await send_dm(self.game_engine, player_obj, prompt_message, need_response=True)

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


    async def redistribute_dice(self, player_name):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            await send_dm(self.game_engine, player_obj, "You are not in the game.")
            return

        # Collect available dice from all players using character names
        available_dice = {p.character.name: [(idx, die) for idx, die in enumerate(p.dice_in_play)]
                          for p in self.player_manager.players.values()}

        # Prompt the player to select a die from each character
        selected_dice = {}
        for char_name, dice in available_dice.items():
            dice_list = "\n".join([f"{idx + 1} - {die}({value})" for idx, (die, value) in dice])
            prompt_message = f"Select a die from {char_name}:\n{dice_list}"
            selected_character, selected_index = await send_dm(self.game_engine, player_obj, prompt_message, need_response=True)
            selected_dice[char_name] = dice[selected_index]
            # Remove the die rome the character
            char_obj = get_player_obj(self.game_engine, char_name)
            char_obj.dice_in_play.remove(dice[selected_index])

        # Prompt the player to redistribute the selected dice
        for target_char_name, (die, value) in selected_dice.items():
            prompt_message = f"Assign {target_char_name}'s {die}({value}) to which character? (Enter character name)"
            new_owner_char_name = await send_dm(self.game_engine, player_obj, prompt_message, need_response=True, double=False)
            new_owner_player = next(
                (p for p in self.player_manager.players.values() if p.character.name == new_owner_char_name), None)
            if not new_owner_player:
                await send_dm(self.game_engine, player_obj, "Invalid character name.")
                return
            new_owner_player.dice_in_play.append((die, value))

    async def handle_jerry_dice(self, player_obj, bonuses):
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
            rolled_dice.extend([(die, die_roll)])
        # List the dice for the player to choose which to discard
        dice_list_msg = "Choose a die to discard:\n" + "\n".join(
            [f"{idx + 1} - {die}({value})" for idx, (die, value) in enumerate(rolled_dice)]
        )
        selected_index = await send_dm(self.game_engine, player_obj, dice_list_msg, need_response=True, double=False)
        if 0 <= selected_index < len(rolled_dice):
            discarded_die = rolled_dice.pop(selected_index)
            for die in rolled_dice:
                player_obj.dice_in_play.append(die)
            await send_dm(self.game_engine, player_obj, f"You discarded {discarded_die}.")
        else:
            await send_dm(self.game_engine, player_obj, "Invalid selection.")

        return bonuses

    async def swap_dice(self, player_name):
        player_requesting = self.players.get(player_name)
        if not player_requesting:
            await self.send_dm(player_requesting.discord_id, "You are not in the game.")
            return

        # Prompt the player to choose a die from two different players
        # Step 1: Choose the first die
        first_die_info = await self.choose_die_for_swap(player_requesting,
                                                        "Choose the first die to swap (format: PlayerName DieNumber):")
        if not first_die_info:
            return  # Handle invalid selection or cancellation

        # Step 2: Choose the second die
        second_die_info = await self.choose_die_for_swap(player_requesting,
                                                         "Choose the second die to swap (format: PlayerName DieNumber):")
        if not second_die_info:
            return  # Handle invalid selection or cancellation

        # Perform the swap
        self.perform_die_swap(first_die_info, second_die_info)
        await self.send_dm(player_requesting.discord_id, "Dice have been swapped.")

    async def choose_die_for_swap(self, player_requesting, prompt_message):
        # List all dice from all players
        dice_list = self.get_all_dice_list()

        # Send the prompt message
        await self.send_dm(player_requesting.discord_id, prompt_message + "\n" + dice_list)

        # Define check for response
        def check(m):
            return m.author.id == player_requesting.discord_id and m.channel.type == discord.ChannelType.private

        try:
            response = await self.bot.wait_for('message', check=check, timeout=60.0)
            selected_player_name, selected_index = response.content.strip().split()
            selected_index = int(selected_index) - 1
            selected_player = self.players.get(selected_player_name)
            selected_die = selected_player.dice_in_play[selected_index]
            return selected_player, selected_die
        except (IndexError, ValueError, asyncio.TimeoutError):
            await self.send_dm(player_requesting.discord_id, "Invalid selection or timeout.")
            return None

    def perform_die_swap(self, first_die_info, second_die_info):
        # Extract the player and die information
        first_player, first_die = first_die_info
        second_player, second_die = second_die_info

        # Remove the dice from the original owners
        first_player.dice_in_play.remove(first_die)
        second_player.dice_in_play.remove(second_die)

        # Swap the dice
        first_player.dice_in_play.append(second_die)
        second_player.dice_in_play.append(first_die)
