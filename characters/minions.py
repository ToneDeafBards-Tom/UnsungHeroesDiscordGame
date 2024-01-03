# Example structure of a Minion
class Minion:
    def __init__(self, name, bonus):
        self.name = name
        self.bonus = bonus

# List of minions
minions = [
    Minion("Minion1", "Bonus1"),
    Minion("Minion2", "Bonus2"),
    Minion("Minion3", "Bonus1"),
    Minion("Minion4", "Bonus2"),

    Minion("Boss", "Final Bonus")
]
