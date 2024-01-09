from characters.minions import Minion


class Tilda:
    def __init__(self):
        self.name = "Tilda"
        self.starting_roll = ["D6"]
        self.deck = [
            {"name": "Good Start", "bonuses": ["+1", "Reroll"], "keyword": ["Item"], "value": 1,
             "image_path": "images/good_start.png"},
            {"name": "Big Stick", "bonuses": ["+4"], "keyword": ["Item"], "value": 4,
             "image_path": "images/big_stick.png"},
            {"name": "Pointy Stick", "bonuses": ["+2"], "keyword": ["Item"], "value": 2,
             "image_path": "images/pointy_stick.png"},
            {"name": "Adequately Sized Staff", "bonuses": ["+3"], "keyword": ["Item"], "value": 3,
             "image_path": "images/adequately_sized_staff.png"},
            {"name": "Note from Mom", "bonuses": ["Reroll Any"], "keyword": ["Item"], "value": 0,
             "image_path": "images/note_from_mom.png"},
            {"name": "Note from Dad", "bonuses": ["Reroll Any"], "keyword": ["Item"], "value": 0,
             "image_path": "images/note_from_dad.png"},
            {"name": "Guild Rejection Notice", "bonuses": ["Nope"], "keyword": [], "value": 0,
             "image_path": "images/guild_rejection_notice.png"},
            {"name": "Skipping Stone", "bonuses": ["D4"], "keyword": ["Item"], "value": 2.5,
             "image_path": "images/skipping_stone.png"},
            {"name": "Square Stone", "bonuses": ["D6"], "keyword": ["Item"], "value": 3.5,
             "image_path": "images/square_stone.png"},
            {"name": "Octa Stone", "bonuses": ["D8"], "keyword": ["Item"], "value": 4.5,
             "image_path": "images/octa_stone.png"},

            {"name": "Sunshine and Happiness", "bonuses": ["D4", "D4"], "keyword": ["Player Card", "Item"], "value": 5,
             "image_path": "images/player_card_5.png"},
            {"name": "Good Karma", "bonuses": ["D6", "Reroll"], "keyword": ["Player Card", "Item"], "value": 3.5,
             "image_path": "images/player_card_6.png"},
            {"name": "Flower Power", "bonuses": ["Reuse", "+3"], "keyword": ["Player Card"], "value": 7,
             "image_path": "images/player_card_d4.png"},
            {"name": "Live and Let Live", "bonuses": ["Reuse", "Reuse"], "keyword": ["Player Card"], "value": 8,
             "image_path": "images/player_card_3xd4.png"},

        ]

        self.gold_card = {"name": "Reduce, Reuse, Recycle", "bonuses": ["Reuse Any", "Reuse Any"],
                          "keyword": ["Player Card", "Gold Card"], "value": 9,
                          "image_path": "images/player_card_9.png"}


rat_bonus = Minion("Rat Bonus", ["+1"])
