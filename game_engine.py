import random
import time
import asyncio

from player_manager import PlayerManager
from game_state import GameState
from card_handler import CardHandler

from helper_functions import roll_dice, add_wanda_die, determine_first_player
from characters.tilda import rat_bonus

class GameEngine:
    def __init__(self, bot):
        self.bot = bot
        self.player_manager = PlayerManager(self, bot)
        self.game_state = GameState(self, self.player_manager)
        self.card_handler = CardHandler(self, self.player_manager, self.game_state, self.bot)
        self.is_final_round = False
        self.current_turn_player_index = 0
        self.player_order = []  # Will hold the order of players
        self.consecutive_passes = 0  # Counter for consecutive passes
        self.game_started = False

    async def start_game(self, ctx):
        if self.player_manager.current_players < 1:  # Assuming at least 2 players are needed
            await ctx.send("Not enough players to start the game.")
            return False

        # Shuffle each player's deck and draw initial cards
        for player_name, player in self.player_manager.players.items():
            self.player_manager.shuffle_player_deck(player_name)
            self.player_manager.draw_cards(player_name, num_cards=5)  # Assuming each player draws 7 cards at the start

        self.player_order = list(self.player_manager.players.keys())
        await self.start_round(ctx)

        await ctx.send("Game has started!")
        self.game_started = True

        return True

    def get_current_player(self):
        return self.player_manager.players[self.player_order[self.current_turn_player_index]]

    async def next_turn(self, ctx, player_name):
        current_player = self.get_current_player()
        print(current_player, player_name, current_player.name)

        if player_name != current_player.name:
            # It's not this player's turn
            await ctx.send(f"It's not your turn, {player_name}.")
            return

        # Increase the consecutive passes counter
        self.consecutive_passes += 1

        if self.consecutive_passes > len(self.player_order):
            # All players have passed in a row, end the round
            await ctx.send("All players have passed. The round is ending.")
            await self.end_round(ctx)
            return

        # Advance to the next player
        self.current_turn_player_index = (self.current_turn_player_index + 1) % len(self.player_order)
        current_player = self.get_current_player()

        await ctx.send(f"It's now {current_player.character.name}'s turn.")

        if current_player.discord_id == "Bot":
            # It's the AI bot's turn
            print('AI Turn...')
            task = asyncio.create_task(current_player.choose_play_card(self, ctx))


    async def start_round(self, ctx):
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
            print(player_name, player, player.character)
            for die in player.character.starting_roll:
                if player.character.name == "Jerry":
                    bonuses = await self.card_handler.handle_jerry_dice(player, [die])
                else:
                    die_roll = roll_dice(die)
                    # Update dice_in_play with detailed roll results
                    player.dice_in_play.extend([(die, die_roll)])
                    if die_roll == 1 and player.character.name == "Wanda":
                        round_message += add_wanda_die(player, die)

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

        # Load up states for first round nope. do it twice since it goes off of next to last card
        for name in self.player_manager.players:
            self.game_state.save_state(name)

        for name in self.player_manager.players:
            self.game_state.save_state(name)

        first_player_name, first_player = determine_first_player(self.player_manager.players)

        print(self.player_order)
        print(first_player)
        self.current_turn_player_index = self.player_order.index(first_player_name)

        await ctx.send(f"Game started. It's {first_player.character.name}'s turn.")

        # Announce the start of the game and whose turn it is
        current_player = self.get_current_player()
        if current_player.discord_id == "Bot":
            # It's the AI bot's turn
            print('New Round AI Turn...')
            task = asyncio.create_task(current_player.choose_play_card(self, ctx))

        return round_message

    async def end_round(self, ctx):
        round_winner = self.determine_winner()
        await ctx.send(f"Round winner: {round_winner.character.name}! See DM for Treasure selection.")
        await self.draw_treasures(round_winner)
        self.prepare_next_round()
        round_start = await self.start_round(ctx)
        if self.is_final_round:
            await ctx.send("***The final round has begun! The boss card is drawn.***")
        game_state = self.game_state.display_game_state()
        await ctx.send(game_state)

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
        for player_name in self.player_manager.players:
            player = self.player_manager.players.get(player_name)
            if player.character.name == "Tilda" and player is not round_winner:
                player.passive_bonus.append("+1")

    def prepare_next_round(self):
        for player in self.player_manager.players.values():
            for card in player.cards_in_play:
                player.discard.append(card)
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
        self.game_started = False




