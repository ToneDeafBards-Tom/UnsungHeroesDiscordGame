class Player:
    def __init__(self, name, character, discord_id):
        self.name = name
        self.character = character
        self.discord_id = discord_id  # Discord ID of the player
        self.is_ready = False  # Flag to track if the player is ready
        self.hand = []
        self.deck = []  # You may initialize the deck here if needed
        self.treasure = []
        self.minions = []
        self.used_minions = []
        self.discard = []
        self.cards_in_play = []
        self.dice_in_play = []
        self.gold_dice = []
        self.score = 0
        self.passive_bonus = [] # for Tilda and probably Karl
