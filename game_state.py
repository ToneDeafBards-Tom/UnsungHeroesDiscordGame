from characters.minions import minions
from characters.treasures import treasure_deck
from helper_functions import get_all_player_objs, get_player_obj, send_dm, send_public_message


class GameState:
    def __init__(self, game_engine, player_manager):
        self.game_engine = game_engine
        self.player_manager = player_manager
        self.current_round = 0
        self.current_turn = 0
        self.current_minion = None
        self.previous_states = {}  # Stores the last two states for each player
        self.last_player = None

    def reset(self):
        self.current_round = 0
        self.current_minion = None
        self.previous_states = {}  # Stores the last two states for each player
        self.last_player = None

    def calculate_score(self, player_name):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            return

        # Example score calculation logic
        player_obj.score = sum(value for _, value in player_obj.dice_in_play)
        player_obj.score += sum(value for _, value in player_obj.gold_dice)

        for card in player_obj.cards_in_play:
            # Handle bonuses on the card
            for bonus in card.get("bonuses", []):
                if bonus.startswith("+1 per"):
                    player_obj.score += min(len(player_obj.dice_in_play), 8)
                elif bonus.startswith("+"):
                    player_obj.score += int(bonus[1:])

        for minion in player_obj.used_minions:
            for bonus in minion.bonus:
                if bonus.startswith("+"):
                    player_obj.score += int(bonus[1:])

        for bonus in player_obj.passive_bonus:
            if bonus.startswith("+"):
                player_obj.score += int(bonus[1:])

    async def display_game_state(self):

        game_state_message = f"---\n**Round Number: {self.current_round}**, Turn {self.current_turn}\n"
        game_state_message += f"Current Minion: {self.current_minion.name}, Bonus: {self.current_minion.bonus}"

        for player_name, player in self.player_manager.players.items():
            cards_in_hand = len(player.hand)
            cards_in_play = ", ".join(card["name"] for card in player.cards_in_play)
            dice_in_play = ", ".join(f"{die}({value})" for die, value in player.dice_in_play)
            gold_dice_in_play = ", ".join(f"{die}({value})" for die, value in player.gold_dice)
            treasure_count = len(player.treasure)
            minion_count = len(player.minions)
            game_state_message += "\n\n"
            game_state_message += (
                f"> Player: **{player.character.name}**\n"
                f"> Cards in hand: {cards_in_hand}, Minions: {minion_count}, Treasures: {treasure_count}\n"
                f"> Cards in play: {cards_in_play}\n"
                f"> Dice in play: {dice_in_play}")
            if gold_dice_in_play:
                game_state_message += f".  Gold Dice: {gold_dice_in_play}"
            game_state_message += f"\n> Score: **{player.score}**"
            if player == self.game_engine.player_obj_in_lead:
                game_state_message += " (winning)"

            game_state_message += "\n"
        game_state_message += "---"
        await send_public_message(self.game_engine, game_state_message)

    def save_state(self, player_name):
        player_obj = get_player_obj(self.game_engine, player_name)
        if player_obj:
            state_snapshot = {
                "dice_in_play": list(player_obj.dice_in_play),
                "cards_in_play": list(player_obj.cards_in_play),
                "score": player_obj.score,
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
            player_obj = get_player_obj(self.game_engine, player_name)
            if player_name in self.previous_states and self.previous_states[player_name][1]:
                previous_state = self.previous_states[player_name][1]
                player_obj.dice_in_play = previous_state["dice_in_play"]
                player_obj.cards_in_play = previous_state["cards_in_play"]
                player_obj.score = previous_state["score"]
                # Revert other player attributes as needed
