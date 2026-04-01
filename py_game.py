import pygame
import random
import json
import argparse
import os
import sys
import math
import glob

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--deck', type=str, help='Use a custom deck')
parser.add_argument('-hp', '--health', type=int, help='Starting health')
args = parser.parse_args()

DEFAULT_HEALTH     = args.health if args.health else 30
selected_deck_path = None
if args.deck and os.path.exists(args.deck):
    selected_deck_path = args.deck

# ── Constants ─────────────────────────────────────────────────────────────────
W, H = 1280, 720
FPS  = 60

C_BG         = (15,  10,  25)
C_PANEL      = (28,  22,  45)
C_PANEL2     = (38,  30,  60)
C_ACCENT     = (200, 160,  60)
C_ACCENT2    = (140,  90, 220)
C_RED        = (200,  60,  60)
C_GREEN      = (60,  180,  80)
C_BLUE       = (60,  140, 200)
C_POISON     = (120, 200,  60)
C_WHITE      = (230, 230, 230)
C_GRAY       = (100,  90, 120)
C_DARK       = (10,    8,  18)
C_CARD_BG    = (35,  28,  55)
C_CARD_HOVER = (55,  45,  85)
C_CARD_SEL   = (80,  60, 130)
C_CARD_BORDER= (80,  65, 110)
C_HP_BG      = (60,  20,  20)
C_HP_FG      = (200,  60,  60)
C_SHIELD_BG  = (20,  30,  60)
C_SHIELD_FG  = (60, 140, 200)

# ── Card class ────────────────────────────────────────────────────────────────
class Card:
    def __init__(self, name, energy_cost, damage, shield, poison, heal=0):
        self.name        = name
        self.energy_cost = energy_cost
        self.damage      = damage
        self.shield      = shield
        self.poison      = poison
        self.heal        = heal

# ── Deck helpers ──────────────────────────────────────────────────────────────
DECK_JSON  = {}
deck_cards = []

def load_deck(path):
    global DECK_JSON, deck_cards
    with open(path, "r") as f:
        DECK_JSON = json.load(f)
    deck_cards = []
    for c in DECK_JSON["CARDS"]:
        for _ in range(c.get("quantity", 1)):
            deck_cards.append(Card(
                c.get("name",        "Unknown"),
                c.get("energy_cost", 0),
                c.get("damage",      0),
                c.get("shield",      0),
                c.get("poison",      0),
                c.get("heal",        0),
            ))

def get_all_decks():
    paths = sorted(glob.glob("decks/*.json"))
    decks = []
    for path in paths:
        try:
            with open(path, "r") as f:
                data = json.load(f)
            decks.append({
                "path":       path,
                "name":       data.get("NAME", os.path.basename(path)),
                "card_count": sum(c.get("quantity", 1) for c in data.get("CARDS", [])),
                "cards":      data.get("CARDS", []),
            })
        except:
            pass
    return decks

def get_deck_image(deck_path):
    deck_name = os.path.splitext(os.path.basename(deck_path))[0]
    img_path  = os.path.join("decks", "img", f"{deck_name}.jpg")
    fallback  = os.path.join("decks", "img", "default_deck.jpg")
    try:
        if os.path.exists(img_path):
            return pygame.image.load(img_path).convert()
        elif os.path.exists(fallback):
            return pygame.image.load(fallback).convert()
    except:
        pass
    return None

# ── Apply damage helper ───────────────────────────────────────────────────────
def apply_damage(damage, enemy_health, enemy_shield):
    if damage >= 0:
        new_health = enemy_health - max(0, damage - enemy_shield)
        new_shield = max(0, enemy_shield - damage)
    else:
        new_health = enemy_health + abs(damage)
        new_shield = enemy_shield
    return new_health, new_shield

# ── AI ────────────────────────────────────────────────────────────────────────
def ai_choose_card(ai_cards, player_health, ai_health, card_to_play, ai_mode="defensive"):
    ai_cards = ai_cards.copy()
    if card_to_play is None:
        card_to_play = Card("empty", 0, 0, 0, 0, 0)

    ai_block  = 0
    ai_energy = 2
    ai_card_to_play = []

    def defend():
        nonlocal ai_energy, ai_block
        if not ai_cards: return False
        best_block = max(ai_cards, key=lambda c: c.shield)
        best_heal  = max(ai_cards, key=lambda c: c.heal)
        has_block  = best_block.shield > 0
        has_heal   = best_heal.heal   > 0
        if has_block or has_heal:
            chosen = best_block if best_block.shield >= best_heal.heal else best_heal
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
        if not ai_cards: return False
        best_dmg = max(ai_cards, key=lambda c: c.damage)
        best_psn = max(ai_cards, key=lambda c: c.poison)
        has_dmg  = best_dmg.damage > 0
        has_psn  = best_psn.poison > 0
        if has_dmg or has_psn:
            if   best_dmg.damage >= player_health:               chosen = best_dmg
            elif best_psn.poison >= player_health:               chosen = best_psn
            elif has_dmg and best_dmg.damage >= best_psn.poison: chosen = best_dmg
            elif has_psn:                                        chosen = best_psn
            else:                                                chosen = best_dmg
            if chosen.energy_cost <= ai_energy:
                ai_card_to_play.append(chosen)
                ai_cards.remove(chosen)
                ai_energy -= chosen.energy_cost
            else:
                return False
        else:
            return False
        return True

    played = False
    while ai_energy > 0:
        danger = card_to_play.damage + card_to_play.poison >= ai_health + ai_block
        if ai_mode == "defensive":
            result = defend() if danger else attack()
        else:
            result = attack()
            if danger and ai_energy > 0:
                result = defend()
        if result:
            played = True
        else:
            if not played:
                ai_card_to_play.append("Draw a card")
            break
    return ai_card_to_play

# ── Pygame init ───────────────────────────────────────────────────────────────
pygame.init()
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Card Duel")
clock  = pygame.time.Clock()

def load_fonts():
    try:
        return {
            "title":  pygame.font.SysFont("Georgia",  32, bold=True),
            "card":   pygame.font.SysFont("Georgia",  16, bold=True),
            "stat":   pygame.font.SysFont("Consolas", 14),
            "small":  pygame.font.SysFont("Consolas", 12),
            "big":    pygame.font.SysFont("Georgia",  48, bold=True),
            "medium": pygame.font.SysFont("Georgia",  22, bold=True),
            "info":   pygame.font.SysFont("Consolas", 15),
        }
    except:
        f = pygame.font.Font(None, 20)
        return {k: f for k in ["title","card","stat","small","big","medium","info"]}

fonts = load_fonts()

# ── Draw helpers ──────────────────────────────────────────────────────────────
def draw_text(surf, text, font_key, color, x, y, center=False, right=False):
    s = fonts[font_key].render(str(text), True, color)
    r = s.get_rect()
    if center: r.centerx = x; r.top  = y
    elif right: r.right  = x; r.top  = y
    else:       r.left   = x; r.top  = y
    surf.blit(s, r)
    return r

def draw_rounded_rect(surf, color, rect, radius=12, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=radius)

def draw_bar(surf, x, y, w, h, value, max_val, bg, fg, label="", radius=6):
    draw_rounded_rect(surf, bg, (x, y, w, h), radius)
    if max_val > 0:
        fill = max(0, int(w * value / max_val))
        if fill > 0:
            draw_rounded_rect(surf, fg, (x, y, fill, h), radius)
    pygame.draw.rect(surf, C_GRAY, (x, y, w, h), 1, border_radius=radius)
    if label:
        draw_text(surf, label, "small", C_WHITE, x + w//2, y + h//2 - 6, center=True)

def draw_button(surf, text, x, y, w, h, hovered=False, disabled=False):
    col    = C_GRAY   if disabled else (C_ACCENT2 if hovered else C_PANEL2)
    border = C_GRAY   if disabled else (C_WHITE   if hovered else C_ACCENT2)
    draw_rounded_rect(surf, col, (x, y, w, h), 8, 2, border)
    tcol = C_GRAY if disabled else C_WHITE
    draw_text(surf, text, "info", tcol, x + w//2, y + h//2 - 9, center=True)
    return pygame.Rect(x, y, w, h)

# ── Card rendering ────────────────────────────────────────────────────────────
CARD_W, CARD_H = 120, 170
CARD_GAP       = 14

def draw_card(surf, card, x, y, hovered=False, selected=False, index=None, playable=True):
    bg = C_CARD_SEL if selected else (C_CARD_HOVER if hovered else C_CARD_BG)
    if not playable:
        bg = (20, 18, 32)

    shadow_surf = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, (0,0,0,100), (0,0,CARD_W,CARD_H), border_radius=10)
    surf.blit(shadow_surf, (x+4, y+4))

    border_col = C_ACCENT if selected else (C_ACCENT2 if hovered else C_CARD_BORDER)
    draw_rounded_rect(surf, bg, (x, y, CARD_W, CARD_H), 10, 2, border_col)
    pygame.draw.rect(surf, C_ACCENT if playable else C_GRAY,
                     (x+2, y+2, CARD_W-4, 4), border_radius=3)

    gem_x, gem_y = x + CARD_W - 22, y + 8
    pygame.draw.circle(surf, C_ACCENT2, (gem_x, gem_y), 12)
    pygame.draw.circle(surf, C_WHITE,   (gem_x, gem_y), 12, 1)
    draw_text(surf, card.energy_cost, "stat", C_WHITE, gem_x, gem_y-8, center=True)

    draw_text(surf, card.name[:13], "card", C_ACCENT if playable else C_GRAY,
              x + CARD_W//2, y + 18, center=True)
    pygame.draw.line(surf, C_CARD_BORDER, (x+8, y+38), (x+CARD_W-8, y+38))

    sy = y + 46
    stats = []
    if card.damage: stats.append(("⚔", f"{card.damage}", C_RED))
    if card.shield: stats.append(("🛡", f"{card.shield}", C_BLUE))
    if card.poison: stats.append(("☠", f"{card.poison}", C_POISON))
    if card.heal:   stats.append(("♥", f"{card.heal}",   C_GREEN))
    for icon, val, col in stats:
        draw_text(surf, icon, "stat", col,     x+14, sy)
        draw_text(surf, val,  "stat", C_WHITE, x+34, sy)
        sy += 22

    if index is not None:
        badge_x, badge_y = x+10, y+CARD_H-22
        pygame.draw.circle(surf, C_ACCENT, (badge_x, badge_y), 10)
        draw_text(surf, index+1, "small", C_DARK, badge_x, badge_y-7, center=True)

    if selected:
        glow = pygame.Surface((CARD_W+16, CARD_H+16), pygame.SRCALPHA)
        pygame.draw.rect(glow, (200,160,60,40), (0,0,CARD_W+16,CARD_H+16), border_radius=14)
        surf.blit(glow, (x-8, y-8))

    return pygame.Rect(x, y, CARD_W, CARD_H)

# ── Stats panel ───────────────────────────────────────────────────────────────
def draw_stats_panel(surf, x, y, w, label, health, max_hp, shield, poison, is_player=True):
    draw_rounded_rect(surf, C_PANEL, (x, y, w, 190), 12, 1, C_CARD_BORDER)
    col = C_ACCENT if is_player else C_ACCENT2
    draw_text(surf, label, "medium", col, x + w//2, y+10, center=True)

    draw_text(surf, "HP", "small", C_GRAY, x+12, y+40)
    draw_bar(surf, x+12, y+56, w-24, 18, health, max_hp,
             C_HP_BG, C_HP_FG, f"{health}/{max_hp}")

    draw_text(surf, "SHIELD", "small", C_GRAY, x+12, y+82)
    draw_bar(surf, x+12, y+98, w-24, 14, shield, max(shield, 20),
             C_SHIELD_BG, C_SHIELD_FG, str(shield))

    draw_text(surf, "POISON", "small", C_GRAY, x+12, y+120)
    pcol = C_POISON if poison > 0 else C_GRAY
    draw_text(surf, f"{poison} stacks", "info", pcol, x+12, y+136)

    draw_text(surf, str(max(0, health)), "title", C_WHITE, x + w//2, y+155, center=True)

# ── Floating text ─────────────────────────────────────────────────────────────
class FloatText:
    def __init__(self, text, x, y, color):
        self.text = text
        self.x, self.y = x, y
        self.color = color
        self.life  = 80
        self.vy    = -1.5

    def update(self):
        self.y    += self.vy
        self.life -= 1

    def draw(self, surf):
        alpha = int(255 * self.life / 80)
        s = fonts["medium"].render(self.text, True, self.color)
        s.set_alpha(alpha)
        surf.blit(s, (self.x - s.get_width()//2, int(self.y)))

float_texts = []

def add_float(text, x, y, color):
    float_texts.append(FloatText(text, x, y, color))

# ── Message log ───────────────────────────────────────────────────────────────
message_log = []

def log(msg, color=C_WHITE):
    message_log.append((msg, color))
    if len(message_log) > 6:
        message_log.pop(0)

def draw_log(surf, x, y, w, h):
    draw_rounded_rect(surf, C_PANEL, (x, y, w, h), 10, 1, C_CARD_BORDER)
    draw_text(surf, "Battle Log", "small", C_ACCENT, x+10, y+6)
    pygame.draw.line(surf, C_CARD_BORDER, (x+8, y+22), (x+w-8, y+22))
    for i, (msg, col) in enumerate(message_log[-5:]):
        draw_text(surf, msg, "small", col, x+10, y+28 + i*18)

# ── Card layout ───────────────────────────────────────────────────────────────
def get_card_positions(n, center_x, y):
    total = n * CARD_W + (n-1) * CARD_GAP
    start = center_x - total // 2
    return [(start + i*(CARD_W+CARD_GAP), y) for i in range(n)]

# ── Game state ────────────────────────────────────────────────────────────────
class GameState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.player_health = DEFAULT_HEALTH
        self.player_poison = 0
        self.player_shield = 0
        self.player_cards  = []
        self.player_energy = 2

        self.ai_health = DEFAULT_HEALTH
        self.ai_poison = 0
        self.ai_shield = 0
        self.ai_cards  = []

        self.cards_to_play   = []
        self.selected_cards  = []
        self.phase           = "player"
        self.winner          = None
        self.ai_action_queue = []
        self.ai_action_timer = 0

        for _ in range(3):
            self.player_cards.append(random.choice(deck_cards))
            self.ai_cards.append(random.choice(deck_cards))

        message_log.clear()
        float_texts.clear()
        log("Battle begins!", C_ACCENT)

    def can_play(self, card):
        return card.energy_cost <= self.player_energy

    def start_ai_turn(self):
        self.phase = "ai"
        card_to_play = self.cards_to_play[0] if self.cards_to_play else None
        actions = ai_choose_card(self.ai_cards, self.player_health,
                                 self.ai_health, card_to_play)
        self.ai_action_queue = actions
        self.ai_action_timer = 0
        log("Opponent is thinking...", C_ACCENT2)

    def process_ai_action(self):
        if not self.ai_action_queue:
            self.end_turn()
            return
        action = self.ai_action_queue.pop(0)
        if action == "Draw a card":
            new = random.choice(deck_cards)
            self.ai_cards.append(new)
            log("Opponent draws a card", C_GRAY)
        else:
            self.ai_cards.remove(action)
            self.player_health, self.player_shield = apply_damage(
                action.damage, self.player_health, self.player_shield)
            self.player_poison += action.poison
            self.ai_shield     += action.shield
            self.ai_health      = min(DEFAULT_HEALTH, self.ai_health + action.heal)

            if action.damage > 0:
                dmg = max(0, action.damage - self.player_shield)
                log(f"Opponent plays {action.name}: -{dmg} HP!", C_RED)
                add_float(f"-{dmg}", W//4, H//2, C_RED)
            elif action.damage < 0:
                log(f"Opponent plays {action.name}: heals you +{abs(action.damage)}!", C_GREEN)
                add_float(f"+{abs(action.damage)}", W//4, H//2, C_GREEN)
            else:
                log(f"Opponent plays {action.name}", C_ACCENT2)

            if action.poison:
                log(f"You are poisoned! (+{action.poison})", C_POISON)
            if action.heal:
                log(f"Opponent heals +{action.heal}", C_GREEN)
                add_float(f"+{action.heal}", 3*W//4, H//3, C_GREEN)

        self.check_death()

    def play_selected(self):
        for idx in sorted(self.selected_cards, reverse=True):
            card = self.player_cards[idx]
            if card.energy_cost <= self.player_energy:
                self.cards_to_play.append(card)
                self.player_energy -= card.energy_cost
                self.ai_health, self.ai_shield = apply_damage(
                    card.damage, self.ai_health, self.ai_shield)
                self.ai_poison     += card.poison
                self.player_shield += card.shield
                self.player_health  = min(DEFAULT_HEALTH, self.player_health + card.heal)
                self.player_cards.pop(idx)

                if card.damage > 0:
                    dmg = max(0, card.damage - self.ai_shield)
                    log(f"You play {card.name}: -{dmg} HP to opponent!", C_ACCENT)
                    add_float(f"-{dmg}", 3*W//4, H//2, C_RED)
                elif card.damage < 0:
                    log(f"You play {card.name}: heals opponent +{abs(card.damage)}!", C_POISON)
                    add_float(f"+{abs(card.damage)}", 3*W//4, H//2, C_GREEN)
                else:
                    log(f"You play {card.name}", C_ACCENT)

                if card.heal:
                    add_float(f"+{card.heal} HP", W//4, H//3, C_GREEN)

        self.selected_cards = []
        self.check_death()

    def draw_card_action(self):
        new = random.choice(deck_cards)
        self.player_cards.append(new)
        log(f"You draw {new.name}", C_BLUE)
        self.end_player_turn()

    def end_player_turn(self):
        self.player_energy = 0
        self.start_ai_turn()

    def end_turn(self):
        self.player_shield = 0
        self.ai_shield     = 0
        self.cards_to_play = []
        self.selected_cards= []

        self.player_health -= self.player_poison
        self.player_poison  = max(0, self.player_poison - 1)
        self.ai_health     -= self.ai_poison
        self.ai_poison      = max(0, self.ai_poison - 1)

        self.player_energy = 2
        self.phase = "player"
        log("── Your turn ──", C_ACCENT)
        self.check_death()

    def check_death(self):
        if self.player_health <= 0:
            self.phase  = "gameover"
            self.winner = "ai"
            log("You have been defeated! 💀", C_RED)
        elif self.ai_health <= 0:
            self.phase  = "gameover"
            self.winner = "player"
            log("You won! 🎉", C_GREEN)

gs = None  # created after deck selection

# ── Deck Select Screen ────────────────────────────────────────────────────────
DCARD_W, DCARD_H = 200, 300
DCARD_GAP        = 30
IMG_W,   IMG_H   = 116, 160

def draw_deck_select(surf, decks, hover_idx, scroll, deck_images, mx, my):
    surf.fill(C_BG)

    # Background grid
    for gx in range(0, W, 60):
        pygame.draw.line(surf, (25,18,40), (gx, 0), (gx, H))
    for gy in range(0, H, 60):
        pygame.draw.line(surf, (25,18,40), (0, gy), (W, gy))

    # Title
    draw_rounded_rect(surf, C_PANEL, (0, 0, W, 60), 0)
    draw_text(surf, "⚔  CARD DUEL", "title", C_ACCENT, W//2, 8, center=True)
    draw_text(surf, "Choose your deck", "medium", C_GRAY, W//2, 38, center=True)

    # Deck cards - 5 per row grid
    DECKS_PER_ROW = 5
    ROW_H         = DCARD_H + 30
    start_y       = 100

    for i, deck_info in enumerate(decks):
        row       = i // DECKS_PER_ROW
        col       = i  % DECKS_PER_ROW
        row_count = min(DECKS_PER_ROW, len(decks) - row * DECKS_PER_ROW)
        total_w   = row_count * (DCARD_W + DCARD_GAP) - DCARD_GAP
        start_x   = W//2 - total_w//2
        cx        = start_x + col * (DCARD_W + DCARD_GAP)
        cy        = start_y + row * ROW_H + scroll
        hovered   = (hover_idx == i)
        offset   = -10 if hovered else 0

        # shadow
        sh = pygame.Surface((DCARD_W, DCARD_H), pygame.SRCALPHA)
        pygame.draw.rect(sh, (0,0,0,80), (0,0,DCARD_W,DCARD_H), border_radius=14)
        surf.blit(sh, (cx+6, cy+6+offset))

        # card body
        border_col = C_ACCENT if hovered else C_CARD_BORDER
        bg_col     = C_CARD_HOVER if hovered else C_CARD_BG
        draw_rounded_rect(surf, bg_col, (cx, cy+offset, DCARD_W, DCARD_H), 14, 2, border_col)

        # deck image - centered
        img = deck_images.get(deck_info["path"])
        img_x = cx + (DCARD_W - IMG_W) // 2  # ✅ centered
        if img:
            scaled = pygame.transform.scale(img, (IMG_W, IMG_H))
            surf.blit(scaled, (img_x, cy+2+offset))
        else:
            # placeholder
            draw_rounded_rect(surf, C_PANEL2, (img_x, cy+2+offset, IMG_W, IMG_H), 12)
            draw_text(surf, "🃏", "big", C_ACCENT2, cx+DCARD_W//2, cy+offset+50, center=True)

        # image overlay gradient
        grad = pygame.Surface((IMG_W, 40), pygame.SRCALPHA)
        for gy2 in range(40):
            alpha = int(200 * gy2 / 40)
            pygame.draw.line(grad, (*C_CARD_BG, alpha), (0, gy2), (IMG_W, gy2))
        surf.blit(grad, (img_x, cy+offset+IMG_H-38))

        # deck name - truncate with "..." if too long ✅
        name = deck_info["name"]
        if fonts["medium"].size(name)[0] > DCARD_W - 10:
            while fonts["medium"].size(name + "...")[0] > DCARD_W - 10 and name:
                name = name[:-1]
            name += "..."
        draw_text(surf, name, "medium", C_ACCENT,
                  cx + DCARD_W//2, cy + offset + IMG_H + 8, center=True)

        # card count
        draw_text(surf, f"{deck_info['card_count']} cards", "small", C_GRAY,
                  cx + DCARD_W//2, cy + offset + IMG_H + 36, center=True)

        # unique card types
        unique = len(deck_info["cards"])
        draw_text(surf, f"{unique} unique types", "small", C_GRAY,
                  cx + DCARD_W//2, cy + offset + IMG_H + 54, center=True)

        # select button
        btn_y = cy + offset + DCARD_H - 44
        btn_hovered = pygame.Rect(cx+10, btn_y, DCARD_W-20, 34).collidepoint(mx, my)
        draw_button(surf, "▶  Select", cx+10, btn_y, DCARD_W-20, 34, btn_hovered)

    # scroll hint if more than one row
    num_rows = (len(decks) + DECKS_PER_ROW - 1) // DECKS_PER_ROW
    if num_rows > 1:
        draw_text(surf, "▲ ▼  scroll", "small", C_GRAY, W//2, H-30, center=True)

def deck_select_loop():
    global selected_deck_path

    # If deck was given via -d arg, skip this screen
    if selected_deck_path:
        load_deck(selected_deck_path)
        return

    decks = get_all_decks()
    if not decks:
        # No decks found, try default
        fallback = "decks/default_deck.json"
        if os.path.exists(fallback):
            load_deck(fallback)
            return
        else:
            print("No decks found in decks/ folder!")
            pygame.quit()
            sys.exit()

    # Preload images
    deck_images = {}
    for d in decks:
        deck_images[d["path"]] = get_deck_image(d["path"])

    scroll    = 0
    hover_idx = -1
    running   = True

    while running:
        dt = clock.tick(FPS)
        mx, my = pygame.mouse.get_pos()

        # hover detection - grid layout
        DECKS_PER_ROW = 5
        ROW_H         = DCARD_H + 30
        hover_idx     = -1
        for i, _ in enumerate(decks):
            row       = i // DECKS_PER_ROW
            col       = i  % DECKS_PER_ROW
            row_count = min(DECKS_PER_ROW, len(decks) - row * DECKS_PER_ROW)
            total_w   = row_count * (DCARD_W + DCARD_GAP) - DCARD_GAP
            start_x   = W//2 - total_w//2
            cx        = start_x + col * (DCARD_W + DCARD_GAP)
            cy        = 100 + row * ROW_H + scroll
            if pygame.Rect(cx, cy, DCARD_W, DCARD_H).collidepoint(mx, my):
                hover_idx = i

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    for i, deck_info in enumerate(decks):
                        row       = i // DECKS_PER_ROW
                        col       = i  % DECKS_PER_ROW
                        row_count = min(DECKS_PER_ROW, len(decks) - row * DECKS_PER_ROW)
                        total_w   = row_count * (DCARD_W + DCARD_GAP) - DCARD_GAP
                        start_x   = W//2 - total_w//2
                        cx        = start_x + col * (DCARD_W + DCARD_GAP)
                        cy        = 100 + row * ROW_H + scroll
                        btn_y     = cy + DCARD_H - 44
                        if pygame.Rect(cx+10, btn_y, DCARD_W-20, 34).collidepoint(mx, my):
                            load_deck(deck_info["path"])
                            selected_deck_path = deck_info["path"]
                            return
                # scroll with mouse wheel
                if event.button == 4: scroll += 60
                if event.button == 5: scroll -= 60

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:   scroll += 60
                if event.key == pygame.K_DOWN: scroll -= 60

        draw_deck_select(screen, decks, hover_idx, scroll, deck_images, mx, my)
        pygame.display.flip()

# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    global gs

    # Show deck select screen first
    deck_select_loop()

    gs = GameState()
    running   = True
    hover_idx = -1

    while running:
        dt = clock.tick(FPS)
        mx, my = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                # ── GAME OVER ──
                if gs.phase == "gameover":
                    # Play Again
                    if pygame.Rect(W//2-80, H//2+60, 160, 44).collidepoint(mx, my):
                        gs.reset()
                    # Change Deck
                    if pygame.Rect(W//2-80, H//2+115, 160, 44).collidepoint(mx, my):
                        global selected_deck_path
                        selected_deck_path = None  # ✅ global'i değiştir
                        deck_select_loop()
                        gs.reset()

                # ── PLAYER TURN ──
                elif gs.phase == "player":
                    positions = get_card_positions(len(gs.player_cards), W//2, H - CARD_H - 20)
                    for i, (cx, cy) in enumerate(positions):
                        if pygame.Rect(cx, cy, CARD_W, CARD_H).collidepoint(mx, my):
                            card = gs.player_cards[i]
                            if gs.can_play(card):
                                if i in gs.selected_cards:
                                    gs.selected_cards.remove(i)
                                else:
                                    gs.selected_cards.append(i)

                    bx = W - 170
                    if pygame.Rect(bx, H//2-30, 150, 40).collidepoint(mx, my):
                        gs.end_player_turn()
                    if pygame.Rect(bx, H//2+20, 150, 40).collidepoint(mx, my):
                        if gs.selected_cards:
                            gs.play_selected()
                    if len(gs.cards_to_play) == 0:
                        if pygame.Rect(bx, H//2+70, 150, 40).collidepoint(mx, my):
                            gs.draw_card_action()

        # ── AI processing ──
        if gs.phase == "ai":
            gs.ai_action_timer += dt
            if gs.ai_action_timer > 700:
                gs.ai_action_timer = 0
                gs.process_ai_action()

        # ── Float texts ──
        for ft in float_texts[:]:
            ft.update()
            if ft.life <= 0:
                float_texts.remove(ft)

        # ── Hover ──
        hover_idx = -1
        if gs.phase == "player":
            positions = get_card_positions(len(gs.player_cards), W//2, H - CARD_H - 20)
            for i, (cx, cy) in enumerate(positions):
                if pygame.Rect(cx, cy, CARD_W, CARD_H).collidepoint(mx, my):
                    hover_idx = i

        # ════════════════════════
        #  DRAW
        # ════════════════════════
        screen.fill(C_BG)

        for gx in range(0, W, 60):
            pygame.draw.line(screen, (25,18,40), (gx, 0), (gx, H))
        for gy in range(0, H, 60):
            pygame.draw.line(screen, (25,18,40), (0, gy), (W, gy))

        draw_rounded_rect(screen, C_PANEL, (0, 0, W, 44), 0)
        draw_text(screen, "⚔  CARD DUEL", "title", C_ACCENT, W//2, 6, center=True)
        draw_text(screen, DECK_JSON.get("NAME", "DECK"), "small", C_GRAY, W-10, 14, right=True)

        draw_stats_panel(screen, 20, 60, 200, "YOU",
                         gs.player_health, DEFAULT_HEALTH,
                         gs.player_shield, gs.player_poison, is_player=True)
        draw_stats_panel(screen, W-220, 60, 200, "OPPONENT",
                         gs.ai_health, DEFAULT_HEALTH,
                         gs.ai_shield, gs.ai_poison, is_player=False)

        draw_rounded_rect(screen, C_PANEL, (W//2-60, 60, 120, 50), 10, 1, C_ACCENT2)
        draw_text(screen, "ENERGY", "small", C_GRAY, W//2, 65, center=True)
        ecol = C_ACCENT if gs.player_energy > 0 else C_RED
        draw_text(screen, f"{gs.player_energy} / 2", "medium", ecol, W//2, 80, center=True)

        phase_text = "YOUR TURN" if gs.phase == "player" else ("OPPONENT'S TURN" if gs.phase == "ai" else "GAME OVER")
        phase_col  = C_ACCENT   if gs.phase == "player" else (C_ACCENT2 if gs.phase == "ai" else C_RED)
        draw_text(screen, phase_text, "medium", phase_col, W//2, 120, center=True)

        ai_positions = get_card_positions(len(gs.ai_cards), W//2, 260)
        for cx, cy in ai_positions:
            draw_rounded_rect(screen, C_PANEL2, (cx, cy, CARD_W, CARD_H), 10, 2, C_ACCENT2)
            pygame.draw.rect(screen, C_CARD_BORDER, (cx+2, cy+2, CARD_W-4, 4), border_radius=3)
            for row in range(3, CARD_H-10, 15):
                for col2 in range(3, CARD_W-10, 15):
                    pygame.draw.circle(screen, C_PANEL, (cx+col2, cy+row), 2)
            draw_text(screen, "?", "title", C_ACCENT2, cx+CARD_W//2, cy+CARD_H//2-20, center=True)

        positions  = get_card_positions(len(gs.player_cards), W//2, H - CARD_H - 20)
        played_any = len(gs.cards_to_play) > 0
        for i, (cx, cy) in enumerate(positions):
            card     = gs.player_cards[i]
            hovered  = (hover_idx == i)
            selected = (i in gs.selected_cards)
            playable = gs.can_play(card) and gs.phase == "player"
            offset   = -18 if (hovered or selected) else 0
            draw_card(screen, card, cx, cy + offset, hovered, selected, i, playable)

        if gs.phase == "player":
            bx = W - 170
            draw_button(screen, "▶  End Turn",   bx, H//2-30, 150, 40,
                        pygame.Rect(bx, H//2-30, 150, 40).collidepoint(mx, my))
            draw_button(screen, "⚔  Play Cards", bx, H//2+20, 150, 40,
                        pygame.Rect(bx, H//2+20, 150, 40).collidepoint(mx, my),
                        len(gs.selected_cards) == 0)
            draw_button(screen, "🃏  Draw Card",  bx, H//2+70, 150, 40,
                        pygame.Rect(bx, H//2+70, 150, 40).collidepoint(mx, my),
                        played_any)

        if gs.selected_cards and gs.phase == "player":
            names = [gs.player_cards[i].name for i in gs.selected_cards]
            draw_rounded_rect(screen, C_PANEL, (240, 60, 180, 30), 8, 1, C_ACCENT)
            draw_text(screen, "▸ " + ", ".join(names), "small", C_ACCENT, 250, 69)

        draw_log(screen, 20, H-160, 300, 150)

        for ft in float_texts:
            ft.draw(screen)

        # Game over overlay
        if gs.phase == "gameover":
            overlay = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))

            if gs.winner == "player":
                draw_text(screen, "VICTORY!",                    "big",    C_ACCENT, W//2, H//2-70, center=True)
                draw_text(screen, "You defeated your opponent!", "medium", C_GREEN,  W//2, H//2,    center=True)
            else:
                draw_text(screen, "DEFEAT",                      "big",    C_RED,    W//2, H//2-70, center=True)
                draw_text(screen, "You have been defeated!",     "medium", C_GRAY,   W//2, H//2,    center=True)

            draw_button(screen, "▶  Play Again",
                        W//2-80, H//2+60, 160, 44,
                        pygame.Rect(W//2-80, H//2+60, 160, 44).collidepoint(mx, my))
            draw_button(screen, "🃏  Change Deck",
                        W//2-80, H//2+115, 160, 44,
                        pygame.Rect(W//2-80, H//2+115, 160, 44).collidepoint(mx, my))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()