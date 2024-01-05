import random


def determine_first_player(players):
    # Sort players by score, minion count, and treasure count
    sorted_players = sorted(players.items(), key=lambda item: (item[1].score, len(item[1].minions), len(item[1].treasure)))

    # Check if the top players are tied
    top_players = [sorted_players[0]]
    for player in sorted_players[1:]:
        player_ob = player[1]
        top_player = top_players[0][1]
        if (player_ob.score == top_player.score and
                len(player_ob.minions) == len(top_player.minions) and
                len(player_ob.treasure) == len(top_player.treasure)):
            top_players.append(player)
        else:
            break

    # If there's a tie, choose randomly among the top players
    if len(top_players) > 1:
        return random.choice(top_players)

    # Otherwise, return the top player
    return top_players[0]


def roll_dice(die):
    if die == "D4":
        return random.randint(1, 4)
    elif die == "D6":
        return random.randint(1, 6)
    elif die == "D8":
        return random.randint(1, 8)
    elif die == "D12":
        return random.randint(1, 12)


def add_wanda_die(player_obj, die):
    die_roll = roll_dice(die)
    player_obj.dice_in_play.extend([(die, die_roll)])
    return f"\nWanda's {die} exploded and got a {die_roll}!"


def get_all_player_objs(game_engine):
    player_objs = [game_engine.player_manager.players.get(player_name) for player_name in
                   game_engine.player_manager.players]
    return player_objs


def determine_lead(player_objs, me):
    player_scores = [player.score for player in player_objs]
    difference = [score - me.score for score in player_scores]
    return max(difference)

