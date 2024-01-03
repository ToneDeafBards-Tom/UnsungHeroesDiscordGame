import random

def roll_dice(dice):
    results = []
    for die in dice:
        if die == "D4":
            results.append(("D4", random.randint(1, 4)))
        elif die == "D6":
            results.append(("D6", random.randint(1, 6)))
        elif die == "D8":
            results.append(("D8", random.randint(1, 8)))
        elif die == "D12":
            results.append(("D12", random.randint(1, 12)))
    return results

