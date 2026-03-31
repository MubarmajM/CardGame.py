import random
import json
import time
import argparse
import os


parser = argparse.ArgumentParser()
parser.add_argument('-d', '--deck',type=str, help='Use a custom deck')
parser.add_argument('-h', '--health', type=int, help='Starting health')

args = parser.parse_args()

if args.deck:
    if os.path.exists(args.deck):
        deck=args.deck
    else:
        print(f"Deck file {args.deck} doesn't exists!")
        deck="decks/default_deck.json"
else:
    deck="decks/default_deck.json"

if args.health:
    DEFAULT_HEALTH = args.health
else:
    DEFAULT_HEALTH = 30


def askint(
        text:str, 
        max:int, 
        min:int=1,
        err_message:str="Please enter a valid number."
        ) -> int:
    """
    **AskInt**
    is a function to ask user to enter an Integer value ( number )
    """
    answer=None
    while not answer in range(min, max+1):
        try:
            answer=int(input(text))
        except(ValueError):
            print(err_message)
    return answer

class Card:
    def __init__(self,name, energy_cost, damage, shield, poison, heal=0):
        self.name=name
        self.energy_cost=energy_cost
        self.damage=damage
        self.shield=shield
        self.poison=poison
        self.heal=heal


def Preview_Card(card:Card):
    name=card.name
    damage=card.damage
    shield=card.shield
    poison=card.poison
    heal=card.heal
    energy_cost=card.energy_cost

    print("┌─────────────┐")
    print(f"│{name[:13]:^13}│")
    print(f"│{'⚡ ' + str(energy_cost):^12}│")
    print("├─────────────┤")
    
    stats = []
    if damage: stats.append(f"ATK  {damage}")
    if shield: stats.append(f"DEF  {shield}")
    if poison: stats.append(f"PSN  {poison}")
    if heal:   stats.append(f"HL {heal}")
    
    for stat in stats:
        print(f"│ {stat:<12}│")
    
    for _ in range(4 - len(stats)):
        print(f"│{'':13}│")
    
    print("└─────────────┘")

def Preview_Cards(cards: list):
    if not cards:
        return

    # 3'erli gruplara böl
    for i in range(0, len(cards), 3):
        group = cards[i:i+3]
        lines = [[] for _ in range(9)]

        for card in group:
            name        = card.name
            damage      = card.damage
            shield      = card.shield
            poison      = card.poison
            heal        = card.heal
            energy_cost = card.energy_cost

            stats = []
            if damage: stats.append(f"ATK  {damage}")
            if shield: stats.append(f"DEF  {shield}")
            if poison: stats.append(f"PSN  {poison}")
            if heal:   stats.append(f"HL {heal}")

            lines[0].append("┌─────────────┐")
            lines[1].append(f"│{name[:13]:^13}│")
            lines[2].append(f"│{'⚡ ' + str(energy_cost):^12}│")
            lines[3].append("├─────────────┤")

            for j in range(4):
                if j < len(stats):
                    lines[4+j].append(f"│ {stats[j]:<12}│")
                else:
                    lines[4+j].append(f"│{'':13}│")

            lines[8].append("└─────────────┘")

        # Numara satırı
        numbers = [f"  {str(i+k+1):^13} " for k in range(len(group))]
        print("  ".join(numbers))

        for row in lines:
            print("  ".join(row))

        print()  # gruplar arası boşluk

def ai_choose_card(ai_cards, player_health, ai_health, card_to_play, ai_mode="defensive"):
    ai_cards = ai_cards.copy()

    if card_to_play is None:
        card_to_play = Card("empty", 0, 0, 0, 0, 0)

    ai_block = 0
    ai_energy = 2
    ai_card_to_play = []

    def defend():
        nonlocal ai_energy, ai_block
        if not ai_cards:
            return False
        best_block_card = max(ai_cards, key=lambda card: card.shield)
        best_heal_card  = max(ai_cards, key=lambda card: card.heal)

        has_block = best_block_card.shield > 0
        has_heal  = best_heal_card.heal > 0

        if has_block or has_heal:
            chosen = best_block_card if best_block_card.shield >= best_heal_card.heal else best_heal_card
            if chosen.energy_cost <= ai_energy:
                ai_card_to_play.append(chosen)
                ai_cards.remove(chosen)  
                ai_energy -= chosen.energy_cost
                ai_block  += chosen.shield
            else:
                return False
        else:
            return False
        return True

    def attack():
        nonlocal ai_energy
        if not ai_cards:
            return False
        best_damage_card = max(ai_cards, key=lambda card: card.damage)
        best_poison_card = max(ai_cards, key=lambda card: card.poison)

        has_damage = best_damage_card.damage > 0
        has_poison = best_poison_card.poison > 0

        if has_damage or has_poison:
            if best_damage_card.damage >= player_health:
                chosen = best_damage_card
            elif best_poison_card.poison >= player_health:
                chosen = best_poison_card
            elif has_damage and best_damage_card.damage >= best_poison_card.poison:
                chosen = best_damage_card
            elif has_poison:
                chosen = best_poison_card
            else:
                chosen = best_damage_card

            if chosen.energy_cost <= ai_energy:
                ai_card_to_play.append(chosen)
                ai_cards.remove(chosen)  
                ai_energy -= chosen.energy_cost
            else:
                return False
        else:
            return False
        return True

    played_a_card = False
    while ai_energy > 0:
        is_in_danger = card_to_play.damage + card_to_play.poison >= ai_health + ai_block

        if ai_mode == "defensive":
            if is_in_danger:
                result = defend()
            else:
                result = attack()

        elif ai_mode == "aggressive":
            result = attack()
            if is_in_danger and ai_energy > 0:
                result = defend()

        if result:
            played_a_card = True
        else:
            if not played_a_card:
                ai_card_to_play.append("Draw a card")
            break
    return ai_card_to_play

with open(deck, "r") as deck_file:
    DECK_JSON=json.load(deck_file)
    deck_cards=[]
    for card in DECK_JSON["CARDS"]:
        for _ in range(card.get("quantity", 1)):
            deck_cards.append(Card(
                card.get("name", "Unknown"),
                card.get("energy_cost", 0),
                card.get("damage", 0),
                card.get("shield", 0),
                card.get("poison", 0),
                card.get("heal", 0),
            ))
    

def Main():
    player_health=DEFAULT_HEALTH
    player_poison=0
    player_shield=0
    player_cards=[]
    player_energy=0

    ai_health=DEFAULT_HEALTH
    ai_poison=0
    ai_shield=0
    ai_cards=[]

    for _ in range(3):
        player_cards.append(random.choice(deck_cards))
        ai_cards.append(random.choice(deck_cards))

    while True:
        player_shield = 0
        ai_shield = 0

        # PLAYER TURN
        player_health -= player_poison
        player_poison = max(0, player_poison-1)
        if player_health <= 0:
            print("You lost! 💀")
            break
        if ai_health <= 0:
            print("You won! 🎉")
            break

        print(f"Your current HP: {player_health}")
        print("Your turn, Please choose an action!")
        print('\n')          
        player_energy=2
        cards_to_play=[]
        played_a_card = len(cards_to_play) > 0

        while player_energy > 0:
            if player_cards:
                print("1 > Choose a card to play")
                if not played_a_card:  # ✅ kart oynamadıysa draw göster
                    print("2 > Draw a new card")
                    print("3 > Pass")
                    choice = askint(">>> ", 3)
                else:
                    print("2 > Pass")  # ✅ kart oynadıysa sadece pass
                    choice = askint(">>> ", 2)

            if player_cards:
                choice = askint(">>> ", 3)
            else:
                choice = askint(">>> ", 2)

            match choice:
                case 1:
                    if player_cards:
                        temp_player_cards = player_cards.copy()
                        while player_energy > 0:
                            Preview_Cards(temp_player_cards)  # ✅ yan yana göster

                            print(f"You have {player_energy} energies!")
                            print(f"Your shield is {player_shield}!")
                            print(f"You have {player_poison} poison!")
                            print("Enter the number of the card you want to play, 0 to cancel")
                            choice = askint(">>> ", len(temp_player_cards), min=0)
                            match choice:
                                case 0:
                                    break
                                case _:
                                    selected = temp_player_cards[choice - 1]
                                    if selected.energy_cost <= player_energy:
                                        cards_to_play.append(selected)
                                        temp_player_cards.remove(selected)
                                        player_energy -= selected.energy_cost
                                        continue
                    else:
                        new_card = random.choice(deck_cards)
                        player_cards.append(new_card)
                        print(f"Drew a new card: {new_card.name}")
                        break

                case 2:
                    if player_cards:
                        new_card = random.choice(deck_cards)
                        player_cards.append(new_card)
                        print(f"Drew a new card: {new_card.name}")
                        break
                    else:
                        print("Passed the turn")
                        break

                case 3:
                    print("Passed the turn")
                    break

        # Play the user cards
        for action in cards_to_play:
            ai_health -= max(0, action.damage - ai_shield)
            ai_shield  = max(0, ai_shield - action.damage)
            ai_poison += action.poison
            player_shield += action.shield
            player_health += action.heal
            player_cards.remove(action)

        if ai_health <= 0:
            print("You won! 🎉")
            break

        # AI Turn
        ai_health -= ai_poison
        ai_poison = max(0, ai_poison-1)

        card_to_play = cards_to_play[0] if cards_to_play else None
        ai_cards_to_play = ai_choose_card(ai_cards, player_health, ai_health, card_to_play)
        print(f"Your opponent chose {[i.name if isinstance(i, Card) else i for i in ai_cards_to_play]}!")
        print(f"Your opponent's health is {ai_health}")
        print(f"Your opponent's poison is {ai_poison}")
        print(f"Your opponent's shield is {ai_shield}")

        for action in ai_cards_to_play:
            if action == "Draw a card":
                ai_cards.append(random.choice(deck_cards))
            else:
                ai_cards.remove(action)
                
                player_health -= max(0, action.damage - player_shield)
                player_shield  = max(0, player_shield - action.damage)
                player_poison += action.poison
                ai_shield += action.shield
                ai_health += action.heal


if __name__=="__main__":
    Main()