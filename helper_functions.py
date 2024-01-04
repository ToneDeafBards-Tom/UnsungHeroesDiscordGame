import random

def roll_dice(die):
    if die == "D4":
        return random.randint(1, 4)
    elif die == "D6":
        return random.randint(1, 6)
    elif die == "D8":
        return random.randint(1, 8)
    elif die == "D12":
        return random.randint(1, 12)

def add_wanda_die(player, die):
    die_roll = roll_dice(die)
    player.dice_in_play.extend([(die, die_roll)])
    return f"\nWanda's {die} exploded and got a {die_roll}!"


