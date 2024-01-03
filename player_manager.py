import random
import asyncio
import discord
from PIL import Image

from player import Player
from characters.alfred import Alfred

characters = {"Alfred": Alfred}


class PlayerManager:
    def __init__(self, game_engine, bot):
        self.players = {}
        self.bot = bot
        self.current_players = 0
        self.max_players = 4
        self.characters = characters
        self.game_engine = game_engine

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
                if self.game_engine.is_final_round:
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

