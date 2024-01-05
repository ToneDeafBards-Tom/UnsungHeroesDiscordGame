import random
import re
import asyncio

from player import Player
from helper_functions import determine_lead, get_all_player_objs


class AIBot(Player):
    def __init__(self, name, character, discord_id, game_engine):
        super().__init__(name, character, discord_id)
        self.game_engine = game_engine

    async def choose_play_card(self, game_engine):
        print("IM THINKING")
        await asyncio.sleep(2)
        player_objs = get_all_player_objs(game_engine)
        print(determine_lead(player_objs, self))
        # determine if winning
        # Implement the AI's decision-making logic here
        # For example, randomly choose an action
        # This is a placeholder logic; you can develop more complex strategies
        playable_cards = [self.hand.index(card) for card in self.hand if "Nope" not in card['bonuses']]
        print("here are my playable cards", playable_cards)
        print("choose one at random")
        card_to_play = random.choice(playable_cards)
        print("choose one at random", card_to_play)
        await self.game_engine.card_handler.play_card(self.name, card_to_play)
        await self.game_engine.game_state.display_game_state()
        await asyncio.sleep(2)
        task = asyncio.create_task(self.game_engine.next_turn(self.name))

    # Add more methods as needed for different game actions
    async def make_choice(self, message):
        if message.startswith("Choose"):
            # Regular expression to match patterns like "Wanda 1 - D8(3)"
            pattern = r"(\w+ \d+) - D\d+\(\d+\)"
            matches = re.findall(pattern, message)
            # Randomly select one of the matches
            if matches:
                selected_die = random.choice(matches)
                print(message)
                print('bot choice', selected_die, matches)
                return selected_die

