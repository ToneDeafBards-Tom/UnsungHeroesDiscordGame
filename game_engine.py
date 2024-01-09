import random
import time
import asyncio

from player_manager import PlayerManager
from game_state import GameState
from card_handler import CardHandler

from helper_functions import (roll_dice, add_wanda_die, send_dm, send_public_message,
                              get_all_player_objs, get_player_obj)
from characters.tilda import rat_bonus


class GameEngine:
    def __init__(self, bot):
        self.bot = bot
        self.ctx = None
        self.player_manager = PlayerManager(self, bot)
        self.game_state = GameState(self, self.player_manager)
        self.card_handler = CardHandler(self, self.player_manager, self.game_state, self.bot)
        self.is_final_round = False
        self.current_turn_player_index = 0
        self.player_order = []  # Will hold the order of players
        self.consecutive_passes = 0  # Counter for consecutive passes
        self.game_started = False
        self.player_obj_in_lead = ""

    def update_ctx(self, ctx):
        self.ctx = ctx

    async def start_game(self):
        if self.player_manager.current_players < 1:  # Assuming at least 2 players are needed
            await send_public_message(self, "Not enough players to start the game.")
            return False

        self.player_order = list(self.player_manager.players.keys())
        await send_public_message(self, "Let the Game Begin!")
        for player_name in self.player_manager.players:
            await self.player_manager.draw_cards(player_name, 7)

        await self.start_round()
        self.game_started = True


    def get_current_player(self):
        return self.player_manager.players[self.player_order[self.current_turn_player_index]]

    async def next_turn(self, player_name):
        current_player = self.get_current_player()
        print(current_player, player_name, current_player.name)

        if player_name != current_player.name:
            # It's not this player's turn
            await send_public_message(self, f"It's not your turn, {player_name}.")
            return

        # Increase the consecutive passes counter
        self.consecutive_passes += 1

        if self.consecutive_passes > len(self.player_order):
            # All players have passed in a row, end the round
            await send_public_message(self, "All players have passed. The round is ending.")
            await self.end_round()
            return

        # Advance to the next player
        self.current_turn_player_index = (self.current_turn_player_index + 1) % len(self.player_order)
        current_player = self.get_current_player()
        self.game_state.current_turn += 1

        first_player_obj = self.determine_player_in_lead()
        self.player_obj_in_lead = first_player_obj

        await send_public_message(self, f"***It's now {current_player.character.name}'s turn.*** ")
        await self.game_state.display_game_state()

        if current_player.discord_id == "Bot":
            # It's the AI bot's turn
            print('AI Turn...')
            task = asyncio.create_task(current_player.choose_play_card(self))

    async def start_round(self):
        round_message = ""
        self.game_state.current_round += 1  # Assuming there's a self.current_round attribute
        # Draw the first minion card and reveal it
        self.game_state.current_minion = self.card_handler.minions.pop(0)  # Assuming self.minions is a list of minion cards

        if len(self.card_handler.minions) < 1:
            self.is_final_round = True

        for player_obj in get_all_player_objs(self):
            player_name = player_obj.name
            if len(player_obj.hand) < 6:
                await self.player_manager.draw_cards(player_name, num_cards=2)
            elif len(player_obj.hand) < 7:
                await self.player_manager.draw_cards(player_name, num_cards=1)

            # Display each player's hand in a private message
            print(player_name, player_obj, player_obj.character)
            for die in player_obj.character.starting_roll:
                if player_obj.character.name == "Jerry":
                    await self.card_handler.handle_jerry_dice(player_obj, [die], is_gold=False)
                else:
                    die_roll = roll_dice(die)
                    # Update dice_in_play with detailed roll results
                    player_obj.dice_in_play.extend([(die, die_roll)])
                    await send_public_message(self, f"\n{player_name} rolled {die} and got {die_roll}.")
                    if die_roll == 1 and player_obj.character.name == "Wanda":
                        round_message = add_wanda_die(player_obj, die)
                        await send_public_message(self, round_message)

            for minion in player_obj.minions:
                for bonus in minion.bonus:
                    if "D4@2" in bonus:
                        player_obj.dice_in_play.extend([("D4", 2)])
                        player_obj.used_minions.append(minion)
                        player_obj.minions.remove(minion)
                    if "+2" in bonus:
                        player_obj.used_minions.append(minion)
                        player_obj.minions.remove(minion)

            # Apply a score bonus or other effect as needed

            # Update score (assuming score is just the sum of roll values)
            self.game_state.calculate_score(player_name)

        # Load up states for first round nope. do it twice since it goes off of next to last card
        for name in self.player_manager.players:
            self.game_state.save_state(name)

        for name in self.player_manager.players:
            self.game_state.save_state(name)

        first_player_obj = self.determine_player_in_lead()
        self.player_obj_in_lead = first_player_obj

        last_play_obj = self.determine_last_player()
        self.current_turn_player_index = self.player_order.index(last_play_obj.name)

        await send_public_message(self, f"***Round {self.game_state.current_round} has started. It's {last_play_obj.character.name}'s turn.*** ")
        self.game_state.current_turn = 1
        await self.game_state.display_game_state()
        # Announce the start of the game and whose turn it is
        current_player = self.get_current_player()
        if current_player.discord_id == "Bot":
            # It's the AI bot's turn
            print('New Round AI Turn...')
            task = asyncio.create_task(current_player.choose_play_card(self))

        return round_message

    def determine_player_in_lead(self):
        # Sort players by score, minion count, and treasure count
        player_objs = get_all_player_objs(self)
        sorted_players = sorted(player_objs, key=lambda player: (-player.score, len(player.minions), len(player.treasure)))
        print('sorted', sorted_players)

        # Check if the top players are tied
        top_players = [sorted_players[0]]
        for player_ob in sorted_players[1:]:
            top_player = top_players[0]
            if (player_ob.score == top_player.score and
                    len(player_ob.minions) == len(top_player.minions) and
                    len(player_ob.treasure) == len(top_player.treasure)):
                top_players.append(player_ob)
            else:
                break

        # If there's a tie, choose randomly among the top players
        if len(top_players) > 1:
            # see if one is top from last time.
            if self.player_obj_in_lead in top_players:
                top_players.remove(self.player_obj_in_lead)
            return random.choice(top_players)

        # Otherwise, return the top player
        return top_players[0]

    def determine_last_player(self):
        # Sort players by score, minion count, and treasure count
        player_objs = get_all_player_objs(self)
        sorted_players = sorted(player_objs, key=lambda player: (player.score, -len(player.minions), -len(player.treasure)))
        print('bottom sorted', sorted_players)

        # Check if the top players are tied
        bottom_players = [sorted_players[0]]
        for player_obj in sorted_players[1:]:
            bottom_player = bottom_players[0]
            if (player_obj.score == bottom_player.score and
                    len(player_obj.minions) == len(bottom_player.minions) and
                    len(player_obj.treasure) == len(bottom_player.treasure)):
                bottom_players.append(player_obj)
            else:
                break

        # If there's a tie, choose randomly among the top players
        if len(bottom_players) > 1:
            # see if one is top from last time.
            return random.choice(bottom_players)

        # Otherwise, return the top player
        return bottom_players[0]

    async def end_round(self):
        round_winner = self.determine_winner()
        await send_public_message(self, f"Round winner: {round_winner.character.name}! See DM for Treasure selection.")
        await self.draw_treasures(round_winner)
        self.prepare_next_round()
        round_start = await self.start_round()
        if self.is_final_round:
            await send_public_message(self, "***The final round has begun! The boss card is drawn.***")


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
        chosen_treasure = await self.player_manager.player_choose_treasure(round_winner.name, drawn_treasures)
        round_winner.treasure.append(chosen_treasure)
        for player_obj in get_all_player_objs(self):
            if player_obj.character.name == "Tilda" and player_obj is not round_winner:
                player_obj.passive_bonus.append("+1")

    def prepare_next_round(self):
        for player_obj in get_all_player_objs(self):
            for card in player_obj.cards_in_play:
                player_obj.discard.append(card)
            player_obj.cards_in_play = []
            player_obj.dice_in_play = []
            player_obj.score = 0
            player_obj.minions = player_obj.used_minions + player_obj.minions
            player_obj.used_minions = []

    def restart_game(self):
        self.player_manager.reset()
        self.game_state.reset()
        self.card_handler.reset()
        self.is_final_round = False
        self.game_started = False




