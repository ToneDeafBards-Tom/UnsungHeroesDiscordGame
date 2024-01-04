class Jerry:
    def __init__(self):
        self.name = "Jerry"
        self.starting_roll = ["D6"]
        self.deck = [
            {"name": "Good Start", "bonuses": ["+1", "Reroll"], "keyword": ["Item"], "image_path": "images/good_start.png"},
            {"name": "Big Stick", "bonuses": ["+4"], "keyword": ["Item"], "image_path": "images/big_stick.png"},
            {"name": "Pointy Stick", "bonuses": ["+2"], "keyword": ["Item"], "image_path": "images/pointy_stick.png"},
            {"name": "Adequately Sized Staff", "bonuses": ["+3"], "keyword": ["Item"], "image_path": "images/adequately_sized_staff.png"},
            {"name": "Note from Mom", "bonuses": ["Reroll Any"], "keyword": ["Item"], "image_path": "images/note_from_mom.png"},
            {"name": "Note from Dad", "bonuses": ["Reroll Any"], "keyword": ["Item"], "image_path": "images/note_from_dad.png"},
            {"name": "Guild Rejection Notice", "bonuses": ["Nope"], "keyword": [], "image_path": "images/guild_rejection_notice.png"},
            {"name": "Skipping Stone", "bonuses": ["D4"], "keyword": ["Item"], "image_path": "images/skipping_stone.png"},
            {"name": "Square Stone", "bonuses": ["D6"], "keyword": ["Item"], "image_path": "images/square_stone.png"},
            {"name": "Octa Stone", "bonuses": ["D8"], "keyword": ["Item"], "image_path": "images/octa_stone.png"},

            {"name": "Aware of Your Environment", "bonuses": ["D6", "Reroll Any"], "keyword": ["Player Card"], "image_path": "images/player_card_5.png"},
            {"name": "Never Get Caught", "bonuses": ["D4", "Swap"], "keyword": ["Player Card", "Defiant Laugh"], "image_path": "images/player_card_6.png"},
            {"name": "Hide in Plain Sight", "bonuses": ["D6", "Swap"], "keyword": ["Player Card", "Defiant Laugh"], "image_path": "images/player_card_d4.png"},
            {"name": "Eyes on the Prize", "bonuses": ["D4", "D8"], "keyword": ["Player Card"], "image_path": "images/player_card_3xd4.png"},
            {"name": "Way of the Rogue", "bonuses": ["Reroll All", "D6", "Swap"], "keyword": ["Player Card", "Gold Card"], "image_path": "images/player_card_9.png"}
        ]

