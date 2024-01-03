import random
import asyncio
import discord
from PIL import Image

from characters.minions import minions
from characters.treasures import treasure_deck

class Player:
    def __init__(self, name, character, discord_id):
        self.name = name
        self.character = character
        self.discord_id = discord_id  # Discord ID of the player
        self.is_ready = False  # Flag to track if the player is ready
        self.hand = []
        self.deck = []  # You may initialize the deck here if needed
        self.treasure = []
        self.minions = []
        self.used_minions = []
        self.discard_pile = []
        self.cards_in_play = []
        self.dice_in_play = []
        self.score = 0
        self.minion_bonus = []

class GameEngine:
    def __init__(self, characters, bot):
        self.characters = characters
        self.bot = bot
        self.players = {}
        self.max_players = 4
        self.current_players = 0
        self.current_round = 0
        self.is_final_round = False

        self.minions = minions[:-1]  # Exclude the boss minion
        self.shuffle_deck(self.minions)
        self.minions.append(minions[-1])  # Add the boss minion at the bottom
        self.current_minion = None

        self.treasures = self.shuffle_deck(treasure_deck)  # List of treasure cards

        self.previous_states = {}  # Stores the last two states for each player
        self.last_player = None

    async def send_dm(self, player_id, message):
        user = await self.bot.fetch_user(player_id)
        dm_channel = await user.create_dm()
        await dm_channel.send(message)

    def add_player(self, player_name, discord_id):
        # Add a new player if not already present and max players not reached
        if player_name not in self.players and self.current_players < self.max_players:
            self.players[player_name] = Player(player_name, None, discord_id)
            self.current_players += 1
            return f"{player_name} has joined the game."
        elif player_name in self.players:
            return f"{player_name} is already in the game."
        else:
            return "Maximum number of players reached."

    def choose_character(self, player_name, character_name):
        if player_name in self.players:
            if character_name in self.characters:
                character_class = self.characters[character_name]
                self.players[player_name].character = character_class()  # Set the character

                # Initialize the player's deck with the character's deck
                self.players[player_name].deck = [card.copy() for card in character_class().deck]

                return f"{player_name} chose {character_name}."
            else:
                return f"{character_name} is not a valid character."
        else:
            return f"{player_name} is not in the game. Please join the game first."

    def shuffle_deck(self, deck):
        random.shuffle(deck)
        return deck

    def shuffle_player_deck(self, player_name):
        player = self.players.get(player_name)
        if player:
            self.shuffle_deck(player.deck)
            return f"{player_name}'s deck has been shuffled."
        else:
            return f"{player_name}, you need to choose a character first."

    def draw_cards(self, player_name, num_cards=7):
        player = self.players.get(player_name)
        if player:
            hand = player.deck[:num_cards]
            player.hand.extend(hand)
            player.deck = player.deck[num_cards:]

            # Extracting card names from the hand
            card_names = [card['name'] for card in hand]

            return f"{player_name} drew {num_cards} cards: {', '.join(card_names)}."
        else:
            return f"{player_name}, you need to choose a character first."

    async def display_hand(self, player_name):
        player = self.players.get(player_name)
        if player:
            hand_message = "Cards:\n"
            hand_message += "\n".join([
                f"{idx + 1} - {card['name']}, {card['bonuses']}"
                for idx, card in enumerate(player.hand)
            ])

            if player.used_minions or player.minions:
                minion_message = "\n\nMinions:\n"
                minion_message += "\n".join([
                    f"{idx + 1 + len(player.hand)} - {minion.name}, {minion.bonus}"
                    for idx, minion in enumerate(player.minions)
                ])

                if player.used_minions and player.minions:
                    minion_message += "\n"

                minion_message += "\n".join([
                    f"Used: {minion.name}, {minion.bonus}"
                    for idx, minion in enumerate(player.used_minions)
                ])
                hand_message += minion_message

            # Add treasures and bonuses to the message
            if player.treasure:
                treasure_message = "\n\nTreasures:\n"
                if self.is_final_round:
                    treasure_message += "\n".join([
                        f"{idx + 1 + len(player.hand) + len(player.minions)} - {card['name']}, {card['bonuses']}"
                        for idx, card in enumerate(player.treasure)
                    ])
                else:
                    treasure_message += "\n".join([
                        f"{card['name']}, {card['bonuses']}"
                        for idx, card in enumerate(player.treasure)
                    ])
                hand_message += treasure_message

            full_message = f"*** New Hand ***\n\n{hand_message}"
            await self.send_dm(player.discord_id, full_message)
        else:
            # Handle error if player not found
            return f"{player_name}, you need to choose a character first."

    async def start_game(self, ctx):
        if self.current_players < 1:  # Assuming at least 2 players are needed
            await ctx.send("Not enough players to start the game.")
            return False

        # Shuffle each player's deck and draw initial cards
        for player_name, player in self.players.items():
            self.shuffle_player_deck(player_name)
            self.draw_cards(player_name, num_cards=5)  # Assuming each player draws 7 cards at the start
            await self.start_round()

        await ctx.send("Game has started!")

        return True

    async def create_combined_image(self, image_paths):
        images = [Image.open(path) for path in image_paths]
        widths, heights = zip(*(i.size for i in images))

        total_width = sum(widths)
        max_height = max(heights)

        new_im = Image.new('RGB', (total_width, max_height))

        x_offset = 0
        for im in images:
            new_im.paste(im, (x_offset, 0))
            x_offset += im.size[0]

        combined_image_path = "path/to/combined_image.png"  # Update this path
        new_im.save(combined_image_path)
        return combined_image_path

    async def play_card(self, player_name, card_number):
        player = self.players.get(player_name)
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
        elif self.is_final_round and num_hand_cards + num_minion_cards < card_number <= num_hand_cards + num_minion_cards + num_treasure_cards:
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
                self.revert_state(player_name)
                response = f"{self.last_player}'s last card was canceled by 'Nope'."
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
                dice_roll = self.roll_dice([bonus])
                player.dice_in_play.extend(dice_roll)
                response += f"\n{player_name} rolled {bonus} and got {dice_roll}."

        # After playing a card, calculate the new score, record last played, and save state
        self.last_player = player_name
        for name in self.players:
            self.calculate_score(name)
            self.save_state(name)

        return response

    async def prompt_reroll(self, player_name, reroll_any):
        player_requesting = self.players.get(player_name)
        if not player_requesting:
            await self.send_dm(player_requesting.discord_id, "No dice available to reroll.")
            return

        # Generate the list of dice with character names
        dice_list = []
        if reroll_any:
            # List all players' dice
            for p_name, p in self.players.items():
                character_name = p.character.name
                for idx, (die, value) in enumerate(p.dice_in_play):
                    dice_list.append(f"{character_name} {idx + 1} - {die}({value})")
        else:
            # List only the requesting player's dice
            character_name = player_requesting.character.name
            for idx, (die, value) in enumerate(player_requesting.dice_in_play):
                dice_list.append(f"{character_name} {idx + 1} - {die}({value})")

        prompt_message = "Choose a die to reroll (format: CharacterName DieNumber):\n" + "\n".join(dice_list)
        await self.send_dm(player_requesting.discord_id, prompt_message)

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
            await self.send_dm(player_requesting.discord_id, "Invalid selection or timeout.")

    def get_player_name_by_character(self, character_name):
        for player_name, player in self.players.items():
            if player.character.name.lower() == character_name.lower():
                return player_name
        return None

    def reroll_die(self, player_name, die_index):
        player = self.players.get(player_name)
        if not player:
            return f"{player_name} is not in the game."

        try:
            # Retrieve the die to reroll
            die_to_reroll = player.dice_in_play[die_index]

            # Perform the reroll
            new_roll = self.roll_dice([die_to_reroll[0]])[0]  # Rerolling the same type of die
            player.dice_in_play[die_index] = new_roll

            return die_to_reroll[0], new_roll
        except IndexError:
            return "\nInvalid die index."

    async def prompt_upgrade_die(self, player_name):
        player_requesting = self.players.get(player_name)
        # Generate a list of upgradeable dice (D4 and D6)
        upgradeable_dice = []
        for p_name, p in self.players.items():
            character_name = p.character.name
            for idx, (die, value) in enumerate(p.dice_in_play):
                if die in ["D4", "D6"]:
                    upgradeable_dice.append(f"{character_name} {idx + 1} - {die}({value})")

        if not upgradeable_dice:
            await self.send_dm(player_requesting.discord_id, "No dice available to upgrade.")
            return

        prompt_message = "Choose a die to upgrade (D4 or D6, format: CharacterName DieNumber):\n" + "\n".join(
            upgradeable_dice)
        await self.send_dm(player_requesting.discord_id, prompt_message)

        def check(m):
            return m.author.id == player_requesting.discord_id and m.channel.type == discord.ChannelType.private

        try:
            response = await self.bot.wait_for('message', check=check, timeout=60.0)
            selected_character, selected_index = response.content.strip().split()
            selected_index = int(selected_index) - 1

            # Find the player and upgrade the die
            selected_player_name = self.get_player_name_by_character(selected_character)
            selected_player = self.players.get(selected_player_name)
            die_to_upgrade = selected_player.dice_in_play[selected_index]

            if die_to_upgrade[0] in ["D4", "D6"]:
                # Upgrade to D8 and increase value by 2
                selected_player.dice_in_play[selected_index] = ("D8", min(die_to_upgrade[1] + 2, 8))
                upgrade_message = f"\n{player_name} upgraded {selected_character}'s {die_to_upgrade[0]} to D8 with a new value of {min(die_to_upgrade[1] + 2, 8)}"
            else:
                upgrade_message = "Selected die cannot be upgraded."

            return upgrade_message

        except (IndexError, ValueError, asyncio.TimeoutError):
            await self.send_dm(player_requesting.discord_id, "Invalid selection or timeout.")

    async def prompt_set_die_value(self, player_name, set_value):
        player_requesting = self.players.get(player_name)
        # Logic to list all dice
        dice_list = []
        for p_name, p in self.players.items():
            character_name = p.character.name
            print(p.dice_in_play)
            for idx, (die, value) in enumerate(p.dice_in_play):
                dice_list.append(f"{character_name} {idx + 1} - {die}({value})")

        prompt_message = "Choose a die to set to value " + str(
            set_value) + " (format: CharacterName DieNumber):\n" + "\n".join(dice_list)
        await self.send_dm(player_requesting.discord_id, prompt_message)

        def check(m):
            return m.author.id == player_requesting.discord_id and m.channel.type == discord.ChannelType.private

        try:
            response = await self.bot.wait_for('message', check=check, timeout=60.0)
            selected_character, selected_index = response.content.strip().split()
            selected_index = int(selected_index) - 1

            # Find the player and set the die's value
            selected_player_name = self.get_player_name_by_character(selected_character)
            selected_player = self.players.get(selected_player_name)
            if selected_index < len(selected_player.dice_in_play):
                selected_player.dice_in_play[selected_index] = (
                selected_player.dice_in_play[selected_index][0], set_value)
                set_message = f"\n{player_name} set {selected_character}'s {selected_player.dice_in_play[selected_index][0]} to {set_value}."
            else:
                set_message = "Invalid die selection."

            return set_message
        except (IndexError, ValueError, asyncio.TimeoutError):
            await self.send_dm(player_requesting.discord_id, "Invalid selection or timeout.")

    def calculate_score(self, player_name):
        player = self.players.get(player_name)
        if not player:
            return

        # Example score calculation logic
        player.score = sum(value for _, value in player.dice_in_play)
        for card in player.cards_in_play:
            # Handle bonuses on the card
            for bonus in card.get("bonuses", []):
                if bonus.startswith("+"):
                    player.score += int(bonus[1:])

        for minion in player.used_minions:
            for bonus in minion.bonus:
                if bonus.startswith("+"):
                    player.score += int(bonus[1:])


    def display_game_state(self):
        game_state_message = f"Round Number: {self.current_round}\n"
        game_state_message += f"Current Minion: {self.current_minion.name}, Bonus: {self.current_minion.bonus}\n\n"

        for player_name, player in self.players.items():
            cards_in_hand = len(player.hand)
            cards_in_play = ", ".join(card["name"] for card in player.cards_in_play)
            dice_in_play = ", ".join(f"{die}({value})" for die, value in player.dice_in_play)
            treasure_count = len(player.treasure)
            minion_count = len(player.minions)
            game_state_message += (
                f"Player: {player_name}\n"
                f"Cards in hand: {cards_in_hand}, Minions: {minion_count}, Treasures: {treasure_count}\n"
                f"Cards in play: {cards_in_play}\n"
                f"Dice in play: {dice_in_play}\n"
                f"Score: {player.score}\n\n"
            )
        return game_state_message

    def roll_dice(self, dice):
        results = []
        for die in dice:
            if die == "D4":
                results.append(("D4", random.randint(1, 4)))
            elif die == "D6":
                results.append(("D6", random.randint(1, 6)))
            elif die == "D8":
                results.append(("D8", random.randint(1, 8)))
            elif die == "D12":
                results.append(("D12", random.randint(1, 12)))
        return results

    async def start_round(self):
        round_message = ""
        self.current_round += 1  # Assuming there's a self.current_round attribute
        # Draw the first minion card and reveal it
        self.current_minion = self.minions.pop(0)  # Assuming self.minions is a list of minion cards

        if len(minions) < 51:
            self.is_final_round = True

        for player_name, player in self.players.items():
            if len(player.hand) < 6:
                self.draw_cards(player.name, num_cards=2)
            elif len(player.hand) < 7:
                self.draw_cards(player.name, num_cards=1)
            # Display each player's hand in a private message

            starting_roll = player.character.starting_roll
            roll_results = self.roll_dice(starting_roll)

            # Update dice_in_play with detailed roll results
            player.dice_in_play.extend(roll_results)

            for minion in player.minions:
                for bonus in minion.bonus:
                    if "D4@2" in bonus:
                        player.dice_in_play.extend([("D4", 2)])
                        player.used_minions.append(minion)
                        player.minions.remove(minion)
                    if "+2" in bonus:
                        player.used_minions.append(minion)
                        player.minions.remove(minion)

            # Apply a score bonus or other effect as needed

            # Update score (assuming score is just the sum of roll values)
            self.calculate_score(player_name)
            await self.display_hand(player_name)

        return round_message

    def determine_winner(self):
        # Determine the round winner
        round_winner = max(self.players.values(), key=lambda p: p.score)
        # Award the top minion card
        round_winner.minions.append(self.current_minion)

        return round_winner

        # Award minion bonus
        # Assuming a method get_minion_bonus() that gives the bonus for the current minion
        # minion_bonus = self.get_minion_bonus()
        # round_winner.minion.append(minion_bonus)

    async def draw_treasures(self, round_winner):
        # Treasure selection process
        # Assuming two treasures are drawn and one is chosen
        drawn_treasures = [self.treasures.pop() for _ in range(2)]
        # Implement logic for player to choose one treasure
        chosen_treasure = await self.player_choose_treasure(round_winner, drawn_treasures)
        round_winner.treasure.append(chosen_treasure)

    async def player_choose_treasure(self, player, treasures):
        treasure_message = "** Choose a Treasure **\n"
        treasure_message += "\n".join([
                        f"{idx + 1} - {card['name']}, {card['bonuses']}"
                        for idx, card in enumerate(treasures)
                    ])
        await self.send_dm(player.discord_id, treasure_message)

        # Wait for player's choice
        def check(m):
            return m.author.id == player.discord_id and m.channel.type == discord.ChannelType.private

        try:
            response = await self.bot.wait_for('message', check=check, timeout=60.0)
            chosen_index = int(response.content.strip()) - 1
            return treasures[chosen_index]
        except (IndexError, ValueError, asyncio.TimeoutError):
            return None  # Or handle invalid choice differently

    def prepare_next_round(self):
        for player in self.players.values():
            player.cards_in_play = []
            player.dice_in_play = []
            player.score = 0
            player.minions = player.used_minions + player.minions
            player.used_minions = []

    def save_state(self, player_name):
        player = self.players.get(player_name)
        if player:
            state_snapshot = {
                "dice_in_play": list(player.dice_in_play),
                "cards_in_play": list(player.cards_in_play),
                "score": player.score,
                # Add other player attributes as needed
            }

            # Save the last two states
            if player_name not in self.previous_states:
                self.previous_states[player_name] = [state_snapshot, None]
            else:
                self.previous_states[player_name][1] = self.previous_states[player_name][0]
                self.previous_states[player_name][0] = state_snapshot

    def revert_state(self, player_name):
        # Revert to the previous state
        player = self.players.get(player_name)
        if player and player_name in self.previous_states and self.previous_states[player_name][1]:
            previous_state = self.previous_states[player_name][1]
            player.dice_in_play = previous_state["dice_in_play"]
            player.cards_in_play = previous_state["cards_in_play"]
            player.score = previous_state["score"]
            # Revert other player attributes as needed

    def restart_game(self):
        self.players = {}
        self.max_players = 4
        self.current_players = 0
        self.current_round = 0
        self.is_final_round = False

        self.minions = minions[:-1]  # Exclude the boss minion
        self.shuffle_deck(self.minions)
        self.minions.append(minions[-1])  # Add the boss minion at the bottom
        self.current_minion = None

        self.treasures = self.shuffle_deck(treasure_deck)  # List of treasure cards

        self.previous_states = {}  # Stores the last two states for each player
        self.last_player = None