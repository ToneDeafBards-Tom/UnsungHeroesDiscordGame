# Example structure of a Minion
class Minion:
    def __init__(self, name, bonus):
        self.name = name
        self.bonus = bonus

# List of minions
minions = [
    Minion("Don't Sous-Chef Rat", ["Upgrade"]),
    Minion("No Regrets rat", ["Reroll"]),
    Minion("Technocratic Rat", ["+2"]),
    Minion("Oopsie Rat", ["D4@2"]),
    Minion("King Rat", ["You Win!"])
]
