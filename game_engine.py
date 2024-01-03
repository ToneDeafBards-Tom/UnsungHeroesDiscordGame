import random
import asyncio
import discord
from PIL import Image

from characters.minions import minions
from characters.treasures import treasure_deck

from player import Player

from player_manager import PlayerManager
from game_state import GameState
from card_handler import CardHandler

class GameEngine:
    def __init__(self, characters, bot):
        self.characters = characters
        self.bot = bot
        self.player_manager = PlayerManager(self, bot)
        self.game_state = GameState(self, self.player_manager)
        self.card_handler = CardHandler(self.player_manager, self.game_state, self.bot)

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

    def prepare_next_round(self):
        for player in self.players.values():
            player.cards_in_play = []
            player.dice_in_play = []
            player.score = 0
            player.minions = player.used_minions + player.minions
            player.used_minions = []


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