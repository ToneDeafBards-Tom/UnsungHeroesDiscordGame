from characters.minions import minions
from characters.treasures import treasure_deck

class GameState:
    def __init__(self, game_engine, player_manager):
        self.game_engine = game_engine
        self.player_manager = player_manager
        self.current_round = 0
        self.current_minion = None
        self.previous_states = {}  # Stores the last two states for each player
        self.last_player = None

    def reset(self):
        self.current_round = 0
        self.current_minion = None
        self.previous_states = {}  # Stores the last two states for each player
        self.last_player = None

    def calculate_score(self, player_name):
        player = self.player_manager.players.get(player_name)
        if not player:
            return

        # Example score calculation logic
        print(player.dice_in_play)
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

    def revert_state(self):
        # Revert to the previous state
        for player_name in self.player_manager.players:
            player = self.player_manager.players.get(player_name)
            if player_name in self.previous_states and self.previous_states[player_name][1]:
                previous_state = self.previous_states[player_name][1]
                player.dice_in_play = previous_state["dice_in_play"]
                player.cards_in_play = previous_state["cards_in_play"]
                player.score = previous_state["score"]
                # Revert other player attributes as needed
