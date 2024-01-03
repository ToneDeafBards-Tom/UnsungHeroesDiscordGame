import random
import asyncio
import discord
from PIL import Image

from characters.minions import minions
from characters.treasures import treasures

class Player:
    def __init__(self, name, character, discord_id):
        self.name = name
        self.character = character
        self.discord_id = discord_id  # Discord ID of the player
        self.is_ready = False  # Flag to track if the player is ready
        self.hand = []
        self.deck = []  # You may initialize the deck here if needed
        self.treasure = []
        self.minion = []
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

        self.minions = minions[:-1]  # Exclude the boss minion
        self.shuffle_deck(self.minions)
        self.minions.append(minions[-1])  # Add the boss minion at the bottom
        self.current_minion = None

        self.treasures = self.shuffle_deck(treasures)  # List of treasure cards

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
            hand_message = "\n".join([
                f"{idx + 1} - Card: {card['name']}, Keywords: {', '.join(card.get('keyword', []))}, Bonuses: {', '.join(card['bonuses'])}"
                for idx, card in enumerate(player.hand)
            ])

            # Add treasures and bonuses to the message
            treasure_info = "\n".join(
                [f"Treasure: {treasure.name}, Effect: {treasure.effect}" for treasure in player.treasure])

            full_message = f"*** New Hand ***\n\n{hand_message}\n\n{treasure_info}"
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

    def play_card(self, player_name, card_number):
        player = self.players.get(player_name)
        if not player:
            return f"{player_name} is not in the game."

        try:
            card = player.hand.pop(card_number - 1)  # Card numbers are 1-indexed
        except IndexError:
            return "Invalid card number."

        player.cards_in_play.append(card)

        # Handle bonuses on the card
        for bonus in card.get("bonuses", []):
            if bonus.startswith("+"):
                player.score += int(bonus[1:])
            elif bonus.startswith("D"):
                dice_roll = self.roll_dice([bonus])
                player.dice_in_play.extend(dice_roll)
                player.score += sum(value for _, value in dice_roll)

        return f"{player_name} played {card['name']}."

    def display_game_state(self):
        game_state_message = f"Round Number: {self.current_round}\n"
        game_state_message += f"Current Minion: {self.current_minion.name}, Bonus: {self.current_minion.bonus}\n\n"

        for player_name, player in self.players.items():
            cards_in_hand = len(player.hand)
            cards_in_play = ", ".join(card["name"] for card in player.cards_in_play)
            dice_in_play = ", ".join(f"{die}({value})" for die, value in player.dice_in_play)
            treasure_count = len(player.treasure)
            minion_count = len(player.minion)
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

        for player_name, player in self.players.items():
            if len(player.hand) < 6:
                self.draw_cards(player.name, num_cards=2)
            elif len(player.hand) < 7:
                self.draw_cards(player.name, num_cards=1)
            # Display each player's hand in a private message
            await self.display_hand(player_name)
            starting_roll = player.character.starting_roll + (player.minion_bonus if player.minion_bonus else ())
            roll_results = self.roll_dice(starting_roll)

            # Update dice_in_play with detailed roll results
            player.dice_in_play.extend(roll_results)

            # Update score (assuming score is just the sum of roll values)
            player.score += sum(value for _, value in roll_results)

            round_message += f"{player_name} rolled: {', '.join(f'{die}({value})' for die, value in roll_results)}. Total score: {player.score}\n"

        return round_message

    def determine_winner(self):
        # Determine the round winner
        round_winner = max(self.players.values(), key=lambda p: p.score)
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
        treasure_message += "\n".join(
            [f"{idx + 1} - {treasure.name}: {treasure.effect}" for idx, treasure in enumerate(treasures, start=0)])
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

