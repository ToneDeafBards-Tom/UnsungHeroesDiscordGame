import asyncio
import discord

class CardHandler:
    def __init__(self, game_engine, player_manager, game_state, bot):
        self.game_engine = game_engine
        self.player_manager = player_manager
        self.game_state = game_state
        self.bot = bot

    async def play_card(self, player_name, card_number):
        player = self.player_manager.players.get(player_name)
        if not player:
            return f"{player_name} is not in the game."

        num_hand_cards = len(player.hand)
        num_minion_cards = len(player.minions)
        num_treasure_cards = len(player.treasure)

        response = ""
        bonuses = []

        if card_number <= num_hand_cards:
            # Regular card play logic for cards in hand
            try:
                card = player.hand.pop(card_number - 1)
                player.cards_in_play.append(card)
                response += f"{player_name} played {card['name']}."
                bonuses.extend(card.get("bonuses", []))
            except IndexError:
                return "Invalid card number."
        elif num_hand_cards < card_number <= num_hand_cards + num_minion_cards:
            # Use minion bonus
            minion_index = card_number - num_hand_cards - 1
            minion = player.minions[minion_index]
            player.minions.remove(minion)
            player.used_minions.append(minion)
            response += f"{player_name} used {minion.name}'s {minion.bonus}"
            bonuses.extend(minion.bonus)
        elif self.game_state.is_final_round and num_hand_cards + num_minion_cards < card_number <= num_hand_cards + num_minion_cards + num_treasure_cards:
            treasure_index = card_number - num_hand_cards - num_minion_cards - 1
            treasure = player.treasure.pop(treasure_index)
            player.cards_in_play.append(treasure)
            response += f"{player_name} played {treasure['name']}."
            bonuses.extend(treasure.get("bonuses", []))
        else:
            return "Invalid card or minion bonus number."

        # Handle bonuses on the card
        for bonus in bonuses:
            if "Nope" in bonus:
                self.game_state.revert_state(player_name)
                response = f"{self.game_state.last_player}'s last card was canceled by 'Nope'."
            elif "Reroll Any" in bonus:
                test = await self.prompt_reroll(player_name, reroll_any=True)
                response += test
            elif "Reroll" in bonus:
                test = await self.prompt_reroll(player_name, reroll_any=False)
                response += test
            elif "Upgrade" in bonus:
                test = await self.prompt_upgrade_die(player_name)
                response += test
            elif "Die@4" in bonus:
                test = await self.prompt_set_die_value(player_name, 4)
                response += test
            elif "D4@2" in bonus:
                player.dice_in_play.extend([("D4", 2)])
                bonus = "D4"
                dice_roll = 2
                response += f"\n{player_name} added a {bonus} set to {dice_roll}."
            elif bonus.startswith("D"):
                dice_roll = self.game_engine.roll_dice([bonus])
                player.dice_in_play.extend(dice_roll)
                response += f"\n{player_name} rolled {bonus} and got {dice_roll}."

        # After playing a card, calculate the new score, record last played, and save state
        self.last_player = player_name
        for name in self.player_manager.players:
            self.game_state.calculate_score(name)
            self.game_state.save_state(name)

        return response

    async def prompt_reroll(self, player_name, reroll_any):
        player_requesting = self.player_manager.players.get(player_name)
        if not player_requesting:
            await self.player_manager.send_dm(player_requesting.discord_id, "No dice available to reroll.")
            return

        # Generate the list of dice with character names
        dice_list = []
        if reroll_any:
            # List all players' dice
            for p_name, p in self.player_manager.players.items():
                character_name = p.character.name
                for idx, (die, value) in enumerate(p.dice_in_play):
                    dice_list.append(f"{character_name} {idx + 1} - {die}({value})")
        else:
            # List only the requesting player's dice
            character_name = player_requesting.character.name
            for idx, (die, value) in enumerate(player_requesting.dice_in_play):
                dice_list.append(f"{character_name} {idx + 1} - {die}({value})")

        prompt_message = "Choose a die to reroll (format: CharacterName DieNumber):\n" + "\n".join(dice_list)
        await self.player_manager.send_dm(player_requesting.discord_id, prompt_message)

        # Wait for player's response in DM
        def check(m):
            return m.author.id == player_requesting.discord_id and m.channel.type == discord.ChannelType.private

        try:
            response = await self.bot.wait_for('message', check=check, timeout=60.0)
            selected_character, selected_index = response.content.strip().split()
            selected_index = int(selected_index) - 1

            # Translate character name back to player name
            selected_player_name = self.get_player_name_by_character(selected_character)
            rerolled, new_roll = self.reroll_die(selected_player_name, selected_index)
            return f"\n{player_name} rerolled {selected_character}'s {rerolled} and got {new_roll}."
        except (IndexError, ValueError, asyncio.TimeoutError):
            await self.player_manager.send_dm(player_requesting.discord_id, "Invalid selection or timeout.")

    def get_player_name_by_character(self, character_name):
        for player_name, player in self.player_manager.players.items():
            if player.character.name.lower() == character_name.lower():
                return player_name
        return None

    def reroll_die(self, player_name, die_index):
        player = self.player_manager.players.get(player_name)
        if not player:
            return f"{player_name} is not in the game."

        try:
            # Retrieve the die to reroll
            die_to_reroll = player.dice_in_play[die_index]

            # Perform the reroll
            new_roll = self.game_engine.roll_dice([die_to_reroll[0]])[0]  # Rerolling the same type of die
            player.dice_in_play[die_index] = new_roll

            return die_to_reroll[0], new_roll
        except IndexError:
            return "\nInvalid die index."

    async def prompt_upgrade_die(self, player_name):
        player_requesting = self.player_manager.players.get(player_name)
        # Generate a list of upgradeable dice (D4 and D6)
        upgradeable_dice = []
        for p_name, p in self.player_manager.players.items():
            character_name = p.character.name
            for idx, (die, value) in enumerate(p.dice_in_play):
                if die in ["D4", "D6"]:
                    upgradeable_dice.append(f"{character_name} {idx + 1} - {die}({value})")

        if not upgradeable_dice:
            await self.player_manager.send_dm(player_requesting.discord_id, "No dice available to upgrade.")
            return

        prompt_message = "Choose a die to upgrade (D4 or D6, format: CharacterName DieNumber):\n" + "\n".join(
            upgradeable_dice)
        await self.player_manager.send_dm(player_requesting.discord_id, prompt_message)

        def check(m):
            return m.author.id == player_requesting.discord_id and m.channel.type == discord.ChannelType.private

        try:
            response = await self.bot.wait_for('message', check=check, timeout=60.0)
            selected_character, selected_index = response.content.strip().split()
            selected_index = int(selected_index) - 1

            # Find the player and upgrade the die
            selected_player_name = self.get_player_name_by_character(selected_character)
            selected_player = self.player_manager.players.get(selected_player_name)
            die_to_upgrade = selected_player.dice_in_play[selected_index]

            if die_to_upgrade[0] in ["D4", "D6"]:
                # Upgrade to D8 and increase value by 2
                selected_player.dice_in_play[selected_index] = ("D8", min(die_to_upgrade[1] + 2, 8))
                upgrade_message = f"\n{player_name} upgraded {selected_character}'s {die_to_upgrade[0]} to D8 with a new value of {min(die_to_upgrade[1] + 2, 8)}"
            else:
                upgrade_message = "Selected die cannot be upgraded."

            return upgrade_message

        except (IndexError, ValueError, asyncio.TimeoutError):
            await self.player_manager.send_dm(player_requesting.discord_id, "Invalid selection or timeout.")

    async def prompt_set_die_value(self, player_name, set_value):
        player_requesting = self.player_manager.players.get(player_name)
        # Logic to list all dice
        dice_list = []
        for p_name, p in self.player_manager.players.items():
            character_name = p.character.name
            print(p.dice_in_play)
            for idx, (die, value) in enumerate(p.dice_in_play):
                dice_list.append(f"{character_name} {idx + 1} - {die}({value})")

        prompt_message = "Choose a die to set to value " + str(
            set_value) + " (format: CharacterName DieNumber):\n" + "\n".join(dice_list)
        await self.player_manager.send_dm(player_requesting.discord_id, prompt_message)

        def check(m):
            return m.author.id == player_requesting.discord_id and m.channel.type == discord.ChannelType.private

        try:
            response = await self.bot.wait_for('message', check=check, timeout=60.0)
            selected_character, selected_index = response.content.strip().split()
            selected_index = int(selected_index) - 1

            # Find the player and set the die's value
            selected_player_name = self.get_player_name_by_character(selected_character)
            selected_player = self.player_manager.players.get(selected_player_name)
            if selected_index < len(selected_player.dice_in_play):
                selected_player.dice_in_play[selected_index] = (
                selected_player.dice_in_play[selected_index][0], set_value)
                set_message = f"\n{player_name} set {selected_character}'s {selected_player.dice_in_play[selected_index][0]} to {set_value}."
            else:
                set_message = "Invalid die selection."

            return set_message
        except (IndexError, ValueError, asyncio.TimeoutError):
            await self.player_manager.send_dm(player_requesting.discord_id, "Invalid selection or timeout.")

    async def redistribute_dice(self, ctx, player_name):
        # Ensure the player exists
        requesting_player = self.player_manager.players.get(player_name)
        if not requesting_player:
            await ctx.send(f"{player_name} is not in the game.")
            return

        # Collect available dice from all players
        available_dice = {name: [(idx, die) for idx, die in enumerate(p.dice_in_play)] for name, p in
                          self.player_manager.players.items()}

        # Prompt the player to redistribute the selected dice
        selected_dice = {}
        for target_player_name, (die, value) in available_dice.items():
            prompt_message = f"Assign {target_player_name}'s {die}({value}) to which player? (Enter player name)"
            await self.player_manager.send_dm(requesting_player.discord_id, prompt_message)

            # Wait for player's response for redistribution
            def check_redist(m):
                return m.author.id == requesting_player.discord_id and m.channel.type == discord.ChannelType.private

            try:
                response = await self.bot.wait_for('message', check=check_redist, timeout=60.0)
                new_owner_name = response.content.strip()
                if new_owner_name not in self.player_manager.players:
                    await self.player_manager.send_dm(requesting_player.discord_id, "Invalid player name.")
                    return
                # Assign the die to the new owner
                self.player_manager.players[new_owner_name].dice_in_play.append((die, value))
            except asyncio.TimeoutError:
                await self.player_manager.send_dm(requesting_player.discord_id, "Timeout in redistribution. Process canceled.")
                return

        # Update the dice in play for each player after redistribution
        for name in self.player_manager.players:
            if name != player_name:
                self.player_manager.players[name].dice_in_play = [d for d in self.player_manager.players[name].dice_in_play if
                                                   d not in selected_dice.values()]

        # Recalculate scores for all players
        for name in self.player_manager.players:
            self.game_state.calculate_score(name)