# Example structure of a Treasure
class Treasure:
    def __init__(self, name, effect):
        self.name = name
        self.bonuses = effect
        self.keyword = ["Treasure"]


# List of treasures
treasures = [
    Treasure("Sewer pipe", ["Redistribute 1"]),
    Treasure("Dihydrogen Oxide", ["+7"]),
    Treasure("Cloak of Visibility", ["Reroll", "Reroll", "Reroll Any", "Reroll Any"]),
    Treasure("Mouse Trap", ["Die@4", "Die@4", "Die@4"]),
    Treasure("Bandana Banana", ["D8", "Reroll Any", "Reroll Any"]),
    Treasure("Utensil Belt", ["D6", "+3"]),
    Treasure("Rat Detector II", ["D4", "D6", "Reroll"]),
    Treasure("Infinite Extending Ladder", ["+1 per Die. Max of +8"]),
    # ... other treasures ...
]
