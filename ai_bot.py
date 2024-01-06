import random
import re
import asyncio

from player import Player
from helper_functions import determine_lead, get_all_player_objs, send_public_message, get_dice_dict


class AIBot(Player):
    def __init__(self, name, character, discord_id, game_engine):
        super().__init__(name, character, discord_id)
        self.game_engine = game_engine
        self.die_to_pick = ""
        self.reroll_value = 0

    async def choose_play_card(self, game_engine):
        self.die_to_pick = ""
        self.reroll_value = 0
        print("IM THINKING")
        await asyncio.sleep(2)
        # get Scores of all players.
        player_objs = get_all_player_objs(game_engine)
        score_deficit = determine_lead(player_objs, self)
        if score_deficit < 0 or self == self.game_engine.player_obj_in_lead:
            await send_public_message(self.game_engine, f"{self.character.name}: I'm in the lead, so pass.")
            task = asyncio.create_task(self.game_engine.next_turn(self.name))
        else:
            # get dict of values
            new_values_dict = self.get_values_cards()

            # Filter out cards where new_value is less than score_deficit
            filtered_values_dict = {idx: val for idx, val in new_values_dict.items() if val > score_deficit}

            # Find the index with the closest value greater than or equal to the deficit
            # if I have a card that lets me win on average, I should take it.
            if filtered_values_dict:  # Check if there are any valid options
                closest_index = min(filtered_values_dict,
                                    key=lambda idx: abs(filtered_values_dict[idx] - score_deficit))
                task = asyncio.create_task(self.game_engine.card_handler.play_card(self.name, closest_index + 1))
            elif len(self.hand) > 4:
                # If I am really close, and I have the cards, I should go for it
                filtered_values_dict = {idx: val for idx, val in new_values_dict.items() if val + 3 > score_deficit}
                closest_index = min(filtered_values_dict,
                                    key=lambda idx: abs(filtered_values_dict[idx] - score_deficit))
                task = asyncio.create_task(self.game_engine.card_handler.play_card(self.name, closest_index + 1))
            elif len(self.treasure) < 1:
                # if I have no treasure, and multiple of my cards can do it, let's go! we are going for it!
                sorted_values = sorted(new_values_dict.values(), reverse=True)
                if len(sorted_values) >= 3:
                    sum_top_three = sum(sorted_values[:3])
                else:
                    sum_top_three = sum(sorted_values)

                if sum_top_three > score_deficit:
                    # Wish me luck!
                    sorted_values_with_indices = sorted(new_values_dict.items(), key=lambda item: item[1], reverse=True)
                    top_card_index = sorted_values_with_indices[0][0]
                    task = asyncio.create_task(self.game_engine.card_handler.play_card(self.name, top_card_index + 1))
                else:
                    # they are really far ahead
                    task = asyncio.create_task(self.game_engine.next_turn(self.name))
            else:
                # maybe wait. let's see how passive this is.
                task = asyncio.create_task(self.game_engine.next_turn(self.name))

    def get_potential_reroll(self, dice_dict, reroll_any=False):
        max_value_die_key = None
        max_value = -100
        if reroll_any:
            other_die_values = [(key, die_info['from_average']) for key, die_info in dice_dict.items()
                                if die_info['character'] != self.character.name]
            if other_die_values:
                max_value_die_key, max_value = max(other_die_values, key=lambda x: x[1])

        # print('other dice', max_value_die_key, max_value)

        # get index of lowest of my dice from average
        my_die_values = [(key, die_info['from_average']) for key, die_info in dice_dict.items()
                         if die_info['character'] == self.character.name]
        min_value_die_key, min_value = min(my_die_values, key=lambda x: x[1])
        min_value = min_value * -1

        if min_value > max_value:
            if self.reroll_value < min_value:
                self.reroll_value = min_value
                self.die_to_pick = min_value_die_key
            return min_value_die_key, min_value

        if self.reroll_value < max_value:
            self.reroll_value = max_value
            self.die_to_pick = max_value_die_key
        self.die_to_pick = max_value_die_key
        return max_value_die_key, max_value

    def get_values_cards(self):
        dice_dict = get_dice_dict(self.game_engine)

        # get dict of values
        new_values_dict = {}
        for card_idx in [self.hand.index(card) for card in self.hand if "Nope" not in card['bonuses']]:
            card = self.hand[card_idx]
            card_value = card["value"]  # Assuming cards have a 'value' attribute
            if "Reroll D12" in card['bonuses']:
                new_values_dict[card_idx] = card_value - 100
            elif "Reroll Any" in card['bonuses']:
                reroll_die_key, reroll_value = self.get_potential_reroll(dice_dict, reroll_any=True)
                new_values_dict[card_idx] = card_value + reroll_value
            elif "Reroll" in card['bonuses']:
                reroll_die_key, reroll_value = self.get_potential_reroll(dice_dict, reroll_any=False)
                new_values_dict[card_idx] = card_value + reroll_value
            else:
                new_values_dict[card_idx] = card_value

        return new_values_dict

    # Add more methods as needed for different game actions
    async def make_choice(self, message):
        if "Choose" in message:
            # Split the message into lines and filter out non-option lines
            options = [line.strip() for line in message.split('\n') if ' - ' in line]
            # Check if 'Wanda 1' is in the options
            if self.die_to_pick and any(self.die_to_pick in option for option in options):
                choice = self.die_to_pick
            else:
                # Randomly choose one of the options
                chosen_option = random.choice(options)
                # Extract just the 'Wanda X' part
                choice = chosen_option.split(' - ')[0]
            print('ai', choice)
            return choice


