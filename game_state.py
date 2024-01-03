from characters.minions import minions
from characters.treasures import treasure_deck

class GameState:
    def __init__(self, game_engine, player_manager):
        self.current_round = 0
        self.is_final_round = False
        self.minions = minions[:-1]  # Exclude the boss minion
        self.treasures = treasure_deck  # List of treasure cards
        self.current_minion = None
        self.game_engine = game_engine
        self.player_manager = player_manager

        self.previous_states = {}  # Stores the last two states for each player
        self.last_player = None

    def calculate_score(self, player_name):
        player = self.player_manager.get(player_name)
        if not player:
            return

        # Example score calculation logic
        player.score = sum(value for _, value in player.dice_in_play)
        for card in player.cards_in_play:
            # Handle bonuses on the card
            for bonus in card.get("bonuses", []):
                if bonus.startswith("+1 per"):
                    player.score += min(len(player.dice_in_play), 8)
                elif bonus.startswith("+"):
                    player.score += int(bonus[1:])

        for minion in player.used_minions:
            for bonus in minion.bonus:
                if bonus.startswith("+"):
                    player.score += int(bonus[1:])

    def display_game_state(self):
        game_state_message = f"Round Number: {self.current_round}\n"
        game_state_message += f"Current Minion: {self.current_minion.name}, Bonus: {self.current_minion.bonus}\n\n"

        for player_name, player in self.player_manager.players.items():
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

    async def start_round(self):
        round_message = ""
        self.current_round += 1  # Assuming there's a self.current_round attribute
        # Draw the first minion card and reveal it
        self.current_minion = self.minions.pop(0)  # Assuming self.minions is a list of minion cards

        if len(minions) < 51:
            self.is_final_round = True

        for player_name, player in self.player_manager.players.items():
            if len(player.hand) < 6:
                self.player_manager.draw_cards(player.name, num_cards=2)
            elif len(player.hand) < 7:
                self.player_manager.draw_cards(player.name, num_cards=1)
            # Display each player's hand in a private message

            starting_roll = player.character.starting_roll
            roll_results = self.game_engine.roll_dice(starting_roll)

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
            await self.player_manager.display_hand(player_name)

        return round_message

    async def draw_treasures(self, round_winner):
        # Treasure selection process
        # Assuming two treasures are drawn and one is chosen
        drawn_treasures = [self.treasures.pop() for _ in range(2)]
        # Implement logic for player to choose one treasure
        chosen_treasure = await self.player_manager.player_choose_treasure(round_winner, drawn_treasures)
        round_winner.treasure.append(chosen_treasure)


    def save_state(self, player_name):
        player = self.player_manager.players.get(player_name)
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
        player = self.player_manager.players.get(player_name)
        if player and player_name in self.previous_states and self.previous_states[player_name][1]:
            previous_state = self.previous_states[player_name][1]
            player.dice_in_play = previous_state["dice_in_play"]
            player.cards_in_play = previous_state["cards_in_play"]
            player.score = previous_state["score"]
            # Revert other player attributes as needed
