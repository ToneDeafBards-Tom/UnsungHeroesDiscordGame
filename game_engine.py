import random

from player_manager import PlayerManager
from game_state import GameState
from card_handler import CardHandler

from helper_functions import roll_dice


class GameEngine:
    def __init__(self, bot):
        self.bot = bot
        self.player_manager = PlayerManager(self, bot)
        self.game_state = GameState(self, self.player_manager)
        self.card_handler = CardHandler(self, self.player_manager, self.game_state, self.bot)
        self.is_final_round = False

    async def start_game(self, ctx):
        if self.player_manager.current_players < 1:  # Assuming at least 2 players are needed
            await ctx.send("Not enough players to start the game.")
            return False

        # Shuffle each player's deck and draw initial cards
        for player_name, player in self.player_manager.players.items():
            self.player_manager.shuffle_player_deck(player_name)
            self.player_manager.draw_cards(player_name, num_cards=5)  # Assuming each player draws 7 cards at the start
            await self.start_round()

        await ctx.send("Game has started!")

        return True

    async def start_round(self):
        round_message = ""
        self.game_state.current_round += 1  # Assuming there's a self.current_round attribute
        # Draw the first minion card and reveal it
        self.game_state.current_minion = self.card_handler.minions.pop(0)  # Assuming self.minions is a list of minion cards

        if len(self.card_handler.minions) < 1:
            self.is_final_round = True

        for player_name, player in self.player_manager.players.items():
            if len(player.hand) < 6:
                self.player_manager.draw_cards(player.name, num_cards=2)
            elif len(player.hand) < 7:
                self.player_manager.draw_cards(player.name, num_cards=1)
            # Display each player's hand in a private message

            starting_roll = player.character.starting_roll
            roll_results = roll_dice(starting_roll)

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
            self.game_state.calculate_score(player_name)
            await self.player_manager.display_hand(player_name)

        return round_message

    def determine_winner(self):
        # Determine the round winner
        round_winner = max(self.player_manager.players.values(), key=lambda p: p.score)
        # Award the top minion card
        round_winner.minions.append(self.game_state.current_minion)

        return round_winner

        # Award minion bonus
        # Assuming a method get_minion_bonus() that gives the bonus for the current minion
        # minion_bonus = self.get_minion_bonus()
        # round_winner.minion.append(minion_bonus)

    async def draw_treasures(self, round_winner):
        # Treasure selection process
        # Assuming two treasures are drawn and one is chosen
        drawn_treasures = [self.card_handler.treasures.pop() for _ in range(2)]
        # Implement logic for player to choose one treasure
        chosen_treasure = await self.player_manager.player_choose_treasure(round_winner, drawn_treasures)
        round_winner.treasure.append(chosen_treasure)

    def prepare_next_round(self):
        for player in self.player_manager.players.values():
            player.cards_in_play = []
            player.dice_in_play = []
            player.score = 0
            player.minions = player.used_minions + player.minions
            player.used_minions = []

    def restart_game(self):
        self.player_manager.reset()
        self.game_state.reset()
        self.card_handler.reset()
        self.is_final_round = False

