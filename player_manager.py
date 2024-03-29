from player import Player
from helper_functions import (send_dm, send_public_message, shuffle_deck, get_player_obj)

from characters.alfred import Alfred
from characters.wanda import Wanda
from characters.jerry import Jerry
from characters.tilda import Tilda
from ai_bot import AIBot

characters = {"Alfred": Alfred, "Wanda": Wanda, "Jerry": Jerry, "Tilda": Tilda}


class PlayerManager:
    def __init__(self, game_engine, bot):
        self.game_engine = game_engine
        self.bot = bot
        self.characters = characters
        self.max_players = 4

        self.players = {}
        self.current_players = 0

    def reset(self):
        self.players = {}
        self.current_players = 0

    async def add_player(self, player_name, discord_id, character_name):
        # Add a new player if not already present and max players not reached
        if player_name not in self.players and self.current_players < self.max_players:
            if character_name in self.characters:
                character_class = self.characters[character_name]
                if discord_id == "Bot":
                    new_player = AIBot(player_name, character_class(), discord_id, self.game_engine)
                else:
                    new_player = Player(player_name, character_class(), discord_id)
                new_player.deck = [card.copy() for card in character_class().deck]
                new_player.deck = shuffle_deck(new_player.deck)
                if new_player.character.name == "Tilda":
                    new_player.deck.append(character_class().gold_card)
                self.players[player_name] = new_player
                self.current_players += 1
                await send_public_message(self.game_engine, f"{player_name} chose {character_name}.")

        elif player_name in self.players:
            return f"{player_name} is already in the game."
        else:
            return "Maximum number of players reached."

    async def draw_cards(self, player_name, num_cards):
        player_obj = get_player_obj(self.game_engine, player_name)
        hand = player_obj.deck[:num_cards]
        player_obj.hand.extend(hand)
        player_obj.deck = player_obj.deck[num_cards:]

        await send_public_message(self.game_engine, f"{player_name} drew {num_cards} cards.")
        await self.display_hand(player_name)

    async def display_hand(self, player_name):
        player_obj = get_player_obj(self.game_engine, player_name)
        if not player_obj:
            return f"{player_name}, you need to choose a character first."

        hand_message = self.construct_hand_message(player_obj)
        minion_message = self.construct_minion_message(player_obj)
        treasure_message = self.construct_treasure_message(player_obj, self.game_engine.is_final_round)

        full_message = f"*** New Hand ***\n{hand_message}{minion_message}{treasure_message}"
        await send_dm(self.game_engine, player_obj, full_message)

    def construct_hand_message(self, player_obj):
        if player_obj.hand:
            return "Cards:\n" + "\n".join(
                f"{idx + 1} - {card['name']}, {card['bonuses']}" for idx, card in enumerate(player_obj.hand)
            )
        return ""

    def construct_minion_message(self, player_obj):
        if player_obj.used_minions or player_obj.minions:
            message = "\n\nMinions:\n"
            message += "\n".join(
                f"{idx + 1 + len(player_obj.hand)} - {minion.name}, {minion.bonus}" for idx, minion in
                enumerate(player_obj.minions)
            )
            if player_obj.used_minions and player_obj.minions:
                message += "\n"
            message += "\n".join(
                f"Used: {minion.name}, {minion.bonus}" for idx, minion in enumerate(player_obj.used_minions)
            )
            return message
        return ""

    def construct_treasure_message(self, player_obj, final_round):
        if player_obj.treasure:
            message = "\n\nTreasures:\n"
            if final_round:
                message += "\n".join(
                    f"{idx + 1 + len(player_obj.hand) + len(player_obj.minions)} - {card['name']}, {card['bonuses']}" for
                    idx, card
                    in enumerate(player_obj.treasure)
                )
            else:
                message += "\n".join(
                    f"{card['name']}, {card['bonuses']}" for idx, card in enumerate(player_obj.treasure)
                )
            return message
        return ""

    async def player_choose_treasure(self, player_name, treasures):
        player_obj = get_player_obj(self.game_engine, player_name)
        treasure_message = "**Choose a Treasure**\n"
        treasure_message += "\n".join([
                        f"{idx + 1} - {card['name']}, {card['bonuses']}"
                        for idx, card in enumerate(treasures)
                    ])
        chosen_index = await send_dm(self.game_engine, player_obj, treasure_message, need_response=True, double=False)
        print(chosen_index)
        return treasures[int(chosen_index)-1]


