"""
╔══════════════════════════════════════════╗
║   GACHA TOWER DEFENSE  —  Python/Pygame  ║
╚══════════════════════════════════════════╝

HOW TO RUN:
    pip install pygame
    python gacha_tower_defense.py

CONTROLS:
    Left-click  → Place selected tower on the map (not on the path)
    R key       → Roll for a random tower (costs currency)
    U key       → Upgrade selected tower (click tower first, then press U)
    G key       → Upgrade your gacha luck (costs currency)
    ESC         → Quit
"""

import pygame
import random
import math
import sys
import os

# ──────────────────────────────────────────────────────────────────────────────
#  CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 1100, 700
FPS = 60
GRID = 40          # cell size

# Colours
WHITE   = (255, 255, 255)
BLACK   = (  0,   0,   0)
GRAY    = (180, 180, 180)
DARK    = ( 40,  40,  40)
BG      = ( 34,  45,  50)
PATH_C  = (210, 180, 140)
GRASS   = ( 60, 100,  55)
PANEL   = ( 25,  30,  40)

RARITY_COLORS = {
    "Common":    (180, 180, 180),
    "Uncommon":  ( 80, 200,  80),
    "Rare":      ( 80, 130, 255),
    "Epic":      (180,  80, 255),
    "Legendary": (255, 200,  50),
}

# Gacha rates (base)
BASE_RATES = {
    "Common":    0.50,
    "Uncommon":  0.25,
    "Rare":      0.15,
    "Epic":      0.07,
    "Legendary": 0.03,
}

ROLL_COST = 80

# ──────────────────────────────────────────────────────────────────────────────
#  PATH  (list of (col, row) waypoints on the 40-px grid)
# ──────────────────────────────────────────────────────────────────────────────
# Game area: columns 0-19, rows 0-14  (800 × 600)
PATH_WAYPOINTS = [
    (0,  2), (4,  2), (4,  6), (8,  6),
    (8,  2), (13, 2), (13,10), (4, 10),
    (4, 13), (19,13),
]

def waypoints_to_pixels(wps):
    """Convert grid waypoints to pixel centres."""
    return [(x * GRID + GRID // 2, y * GRID + GRID // 2) for x, y in wps]

PIXEL_PATH = waypoints_to_pixels(PATH_WAYPOINTS)

def path_cells():
    """Return a set of (col, row) cells that the path passes through."""
    cells = set()
    for i in range(len(PATH_WAYPOINTS) - 1):
        x0, y0 = PATH_WAYPOINTS[i]
        x1, y1 = PATH_WAYPOINTS[i + 1]
        if x0 == x1:
            for r in range(min(y0, y1), max(y0, y1) + 1):
                cells.add((x0, r))
        else:
            for c in range(min(x0, x1), max(x0, x1) + 1):
                cells.add((c, y0))
    return cells

PATH_CELLS = path_cells()

# ──────────────────────────────────────────────────────────────────────────────
#  TOWER DEFINITIONS
# ──────────────────────────────────────────────────────────────────────────────
TOWER_TEMPLATES = {
    # name: (rarity, damage, range_px, fire_rate_ticks, color, shape)
    "Pebble Slinger": ("Common",    8,  110, 55, (180,180,180), "circle"),
    "Stick Guard":    ("Common",   10,  100, 60, (160,120, 60), "square"),
    "Iron Archer":    ("Uncommon", 20,  140, 45, ( 80,200, 80), "triangle"),
    "Stone Cannon":   ("Uncommon", 28,  120, 70, (100,160, 80), "circle"),
    "Frost Mage":     ("Rare",     22,  150, 40, ( 80,180,255), "diamond"),
    "Shadow Blade":   ("Rare",     35,  110, 35, (130, 60,180), "triangle"),
    "Thunder Drake":  ("Epic",     50,  160, 30, (200,100,255), "circle"),
    "Lava Titan":     ("Epic",     65,  130, 50, (255,100, 30), "square"),
    "Celestial Sage": ("Legendary",90,  200, 25, (255,220, 50), "diamond"),
    "Void Reapers":   ("Legendary",120, 170, 20, (200, 50,255), "triangle"),
}

# ──────────────────────────────────────────────────────────────────────────────
#  ENEMY DEFINITIONS  (scale with wave)
# ──────────────────────────────────────────────────────────────────────────────
ENEMY_TYPES = [
    {"name": "Slime",     "base_hp":  60, "speed": 1.5, "reward":  8, "color": ( 80,200, 80), "shape": "circle", "size": 12},
    {"name": "Goblin",    "base_hp":  90, "speed": 2.0, "reward": 12, "color": (100,180, 60), "shape": "triangle","size": 14},
    {"name": "Orc",       "base_hp": 180, "speed": 1.2, "reward": 18, "color": (120, 80, 40), "shape": "square", "size": 16},
    {"name": "Dark Knight","base_hp":300, "speed": 1.0, "reward": 30, "color": ( 80, 80,180), "shape": "diamond","size": 18},
    {"name": "Dragon",    "base_hp": 600, "speed": 0.9, "reward": 60, "color": (220, 60, 60), "shape": "circle", "size": 22},
]

# ──────────────────────────────────────────────────────────────────────────────
#  HELPER DRAWING FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────
def draw_shape(surf, color, shape, cx, cy, size):
    if shape == "circle":
        pygame.draw.circle(surf, color, (cx, cy), size)
    elif shape == "square":
        pygame.draw.rect(surf, color, (cx - size, cy - size, size * 2, size * 2))
    elif shape == "triangle":
        pts = [(cx, cy - size), (cx - size, cy + size), (cx + size, cy + size)]
        pygame.draw.polygon(surf, color, pts)
    elif shape == "diamond":
        pts = [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)]
        pygame.draw.polygon(surf, color, pts)

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

# ──────────────────────────────────────────────────────────────────────────────
#  CLASSES
# ──────────────────────────────────────────────────────────────────────────────

class Tower:
    def __init__(self, name, gx, gy):
        tpl = TOWER_TEMPLATES[name]
        self.name      = name
        self.rarity    = tpl[0]
        self.damage    = tpl[1]
        self.range_px  = tpl[2]
        self.fire_rate = tpl[3]   # ticks between shots
        self.color     = tpl[4]
        self.shape     = tpl[5]
        self.gx, self.gy = gx, gy
        self.px = gx * GRID + GRID // 2
        self.py = gy * GRID + GRID // 2
        self.cooldown  = 0
        self.level     = 1
        self.target    = None
        self.flash     = 0   # attack flash animation counter

    def upgrade_cost(self):
        return 60 * self.level

    def upgrade(self):
        self.level    += 1
        self.damage   = int(self.damage * 1.4)
        self.range_px = int(self.range_px * 1.1)
        self.fire_rate = max(8, int(self.fire_rate * 0.85))

    def update(self, enemies, projectiles):
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.flash > 0:
            self.flash -= 1

        # find nearest enemy in range
        best = None
        best_prog = -1
        for e in enemies:
            dist = math.hypot(e.px - self.px, e.py - self.py)
            if dist <= self.range_px and e.progress > best_prog:
                best = e
                best_prog = e.progress

        self.target = best
        if best and self.cooldown == 0:
            projectiles.append(Projectile(self.px, self.py, best, self.damage, self.color))
            self.cooldown = self.fire_rate
            self.flash = 6

    def draw(self, surf, selected=False):
        size = GRID // 2 - 4
        # glow if selected
        if selected:
            pygame.draw.circle(surf, (255, 255, 100), (self.px, self.py), size + 8, 2)
        # range ring on hover/select
        if selected:
            ring_surf = pygame.Surface((self.range_px * 2 + 4, self.range_px * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (255, 255, 255, 40),
                               (self.range_px + 2, self.range_px + 2), self.range_px)
            surf.blit(ring_surf, (self.px - self.range_px - 2, self.py - self.range_px - 2))

        flash_color = lerp_color(self.color, WHITE, self.flash / 10) if self.flash else self.color
        draw_shape(surf, flash_color, self.shape, self.px, self.py, size)

        # rarity border ring
        rc = RARITY_COLORS[self.rarity]
        pygame.draw.circle(surf, rc, (self.px, self.py), size + 3, 2)

        # level badge
        if self.level > 1:
            font_sm = pygame.font.SysFont("consolas", 11, bold=True)
            lbl = font_sm.render(f"L{self.level}", True, WHITE)
            surf.blit(lbl, (self.px - lbl.get_width() // 2, self.py - size - 14))


class Enemy:
    def __init__(self, etype, wave):
        t = ENEMY_TYPES[etype % len(ENEMY_TYPES)]
        scale    = 1 + (wave - 1) * 0.18
        self.name    = t["name"]
        self.hp      = int(t["base_hp"] * scale)
        self.max_hp  = self.hp
        self.speed   = t["speed"]
        self.reward  = t["reward"]
        self.color   = t["color"]
        self.shape   = t["shape"]
        self.size    = t["size"]
        self.wp_idx  = 0
        self.px, self.py = PIXEL_PATH[0]
        self.progress = 0.0   # total distance traveled (for targeting)
        self.alive   = True
        self.reached_end = False

    def update(self):
        if self.wp_idx + 1 >= len(PIXEL_PATH):
            self.reached_end = True
            return
        tx, ty = PIXEL_PATH[self.wp_idx + 1]
        dx, dy  = tx - self.px, ty - self.py
        dist    = math.hypot(dx, dy)
        if dist < self.speed:
            self.px, self.py = tx, ty
            self.wp_idx += 1
            self.progress += dist
        else:
            self.px += dx / dist * self.speed
            self.py += dy / dist * self.speed
            self.progress += self.speed

    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False

    def draw(self, surf):
        draw_shape(surf, self.color, self.shape, int(self.px), int(self.py), self.size)
        # health bar
        bar_w = self.size * 2
        ratio = max(0, self.hp / self.max_hp)
        pygame.draw.rect(surf, (120, 0, 0), (int(self.px) - self.size, int(self.py) - self.size - 8, bar_w, 5))
        pygame.draw.rect(surf, (0, 220, 60), (int(self.px) - self.size, int(self.py) - self.size - 8, int(bar_w * ratio), 5))


class Projectile:
    def __init__(self, x, y, target, damage, color):
        self.x, self.y = float(x), float(y)
        self.target    = target
        self.damage    = damage
        self.color     = color
        self.speed     = 8.0
        self.alive     = True

    def update(self):
        if not self.target.alive:
            self.alive = False
            return
        dx = self.target.px - self.x
        dy = self.target.py - self.y
        dist = math.hypot(dx, dy)
        if dist < self.speed:
            self.target.take_damage(self.damage)
            self.alive = False
        else:
            self.x += dx / dist * self.speed
            self.y += dy / dist * self.speed

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), 5)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), 3)


class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = float(x), float(y)
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-4, -1)
        self.life = random.randint(20, 40)
        self.max_life = self.life
        self.color = color
        self.size  = random.randint(2, 5)

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.2
        self.life -= 1

    def draw(self, surf):
        alpha = int(255 * self.life / self.max_life)
        c = (*self.color[:3], alpha)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, c, (self.size, self.size), self.size)
        surf.blit(s, (int(self.x) - self.size, int(self.y) - self.size))


# ──────────────────────────────────────────────────────────────────────────────
#  GACHA SYSTEM
# ──────────────────────────────────────────────────────────────────────────────

def gacha_roll(luck_level=0):
    """Roll a random tower name based on current rarity rates."""
    bonus = luck_level * 0.015
    rates = dict(BASE_RATES)
    rates["Common"]    = max(0.05, rates["Common"]    - bonus * 3)
    rates["Uncommon"]  = max(0.05, rates["Uncommon"]  - bonus)
    rates["Rare"]      = rates["Rare"]      + bonus * 1.5
    rates["Epic"]      = rates["Epic"]      + bonus * 1.2
    rates["Legendary"] = rates["Legendary"] + bonus * 0.8
    # normalise
    total = sum(rates.values())
    rates = {k: v / total for k, v in rates.items()}

    roll = random.random()
    cumulative = 0
    chosen_rarity = "Common"
    for rarity, prob in rates.items():
        cumulative += prob
        if roll < cumulative:
            chosen_rarity = rarity
            break

    # pick a tower of that rarity
    candidates = [n for n, t in TOWER_TEMPLATES.items() if t[0] == chosen_rarity]
    return random.choice(candidates)


# ──────────────────────────────────────────────────────────────────────────────
#  WAVE SPAWNER
# ──────────────────────────────────────────────────────────────────────────────

class WaveSpawner:
    def __init__(self):
        self.wave       = 0
        self.spawned    = 0
        self.to_spawn   = 0
        self.spawn_tick = 0
        self.spawn_interval = 60   # ticks between spawns
        self.active     = False
        self.between    = True     # waiting to start next wave
        self.between_timer = 0

    def start_wave(self):
        self.wave      += 1
        self.spawned    = 0
        self.to_spawn   = 8 + self.wave * 3
        self.active     = True
        self.between    = False
        self.spawn_tick = 0

    def update(self, enemies):
        if self.between:
            self.between_timer -= 1
            if self.between_timer <= 0:
                self.start_wave()
            return

        if not self.active:
            return

        self.spawn_tick -= 1
        if self.spawn_tick <= 0 and self.spawned < self.to_spawn:
            etype = random.randint(0, min(4, self.wave - 1 + 2))  # unlock harder types each wave
            enemies.append(Enemy(etype, self.wave))
            self.spawned    += 1
            self.spawn_tick  = max(20, self.spawn_interval - self.wave * 2)

        if self.spawned >= self.to_spawn and len(enemies) == 0:
            self.active       = False
            self.between      = True
            self.between_timer = FPS * 5  # 5 second break

    def progress_text(self):
        if self.between:
            secs = max(0, self.between_timer // FPS)
            return f"Wave {self.wave} complete! Next in {secs}s"
        return f"Wave {self.wave}  —  {self.spawned}/{self.to_spawn} spawned"


# ──────────────────────────────────────────────────────────────────────────────
#  ROLL RESULT POPUP
# ──────────────────────────────────────────────────────────────────────────────

class RollPopup:
    def __init__(self, tower_name):
        tpl = TOWER_TEMPLATES[tower_name]
        self.name    = tower_name
        self.rarity  = tpl[0]
        self.color   = tpl[4]
        self.shape   = tpl[5]
        self.timer   = FPS * 3   # show for 3 seconds
        self.font_lg = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_sm = pygame.font.SysFont("consolas", 15)

    def update(self):
        self.timer -= 1

    def draw(self, surf):
        if self.timer <= 0:
            return
        alpha = min(255, self.timer * 6)
        panel = pygame.Surface((300, 90), pygame.SRCALPHA)
        panel.fill((20, 20, 40, 200))
        surf.blit(panel, (SCREEN_W - 320, 10))

        rc = RARITY_COLORS[self.rarity]
        pygame.draw.rect(surf, rc, (SCREEN_W - 320, 10, 300, 90), 2)

        draw_shape(surf, self.color, self.shape, SCREEN_W - 290, 55, 16)

        name_surf = self.font_lg.render(self.name, True, WHITE)
        rar_surf  = self.font_sm.render(f"★ {self.rarity}", True, rc)
        surf.blit(name_surf, (SCREEN_W - 265, 18))
        surf.blit(rar_surf,  (SCREEN_W - 265, 48))


# ──────────────────────────────────────────────────────────────────────────────
#  MAIN GAME
# ──────────────────────────────────────────────────────────────────────────────

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Gacha Tower Defense")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()

        self.font_lg = pygame.font.SysFont("consolas", 20, bold=True)
        self.font_md = pygame.font.SysFont("consolas", 16)
        self.font_sm = pygame.font.SysFont("consolas", 13)

        self.reset()

    def reset(self):
        self.towers      = []
        self.enemies     = []
        self.projectiles = []
        self.particles   = []

        self.currency    = 200
        self.base_hp     = 20
        self.max_hp      = 20

        self.luck_level  = 0
        self.luck_cost   = 150

        self.inventory   = []      # list of tower names waiting to be placed
        self.selected_inv = None   # index in inventory of tower to place
        self.selected_tower = None # placed tower index (for upgrading)

        self.spawner     = WaveSpawner()
        self.spawner.between_timer = FPS * 3   # short first delay

        self.popup       = None
        self.game_over   = False
        self.victory     = False
        self.tick        = 0

    # ── MAP DRAWING ──────────────────────────────────────────────────────────

    def draw_map(self):
        # grass background
        self.screen.fill(GRASS)
        # path
        if len(PIXEL_PATH) > 1:
            pygame.draw.lines(self.screen, PATH_C, False, PIXEL_PATH, GRID - 4)
        # path nodes
        for pt in PIXEL_PATH:
            pygame.draw.circle(self.screen, (200, 165, 120), pt, GRID // 2 - 2)
        # start / end markers
        pygame.draw.circle(self.screen, (50, 200, 50),  PIXEL_PATH[0],  10)
        pygame.draw.circle(self.screen, (220, 50, 50),  PIXEL_PATH[-1], 10)

        # right panel separator
        pygame.draw.rect(self.screen, PANEL, (SCREEN_W - 300, 0, 300, SCREEN_H))

    # ── UI ───────────────────────────────────────────────────────────────────

    def draw_ui(self):
        px = SCREEN_W - 295
        y  = 10

        def label(txt, col=WHITE, big=False):
            nonlocal y
            f = self.font_lg if big else self.font_md
            s = f.render(txt, True, col)
            self.screen.blit(s, (px, y))
            y += s.get_height() + 4

        label("GACHA  TOWER  DEFENSE", (255, 220, 50), big=True)
        y += 4

        # HP bar
        bar_w = 280
        hp_ratio = self.base_hp / self.max_hp
        pygame.draw.rect(self.screen, (100, 0,   0), (px, y, bar_w, 18))
        pygame.draw.rect(self.screen, (220, 50,  50), (px, y, int(bar_w * hp_ratio), 18))
        hp_txt = self.font_sm.render(f"♥  {self.base_hp} / {self.max_hp}", True, WHITE)
        self.screen.blit(hp_txt, (px + 5, y + 2))
        y += 26

        label(f"💰  {self.currency} gold")
        label(self.spawner.progress_text(), (180, 200, 255))

        y += 6
        # ROLL button
        roll_col = (255, 200, 50) if self.currency >= ROLL_COST else (100, 100, 100)
        pygame.draw.rect(self.screen, roll_col, (px, y, 135, 32), border_radius=6)
        r_txt = self.font_md.render(f"[R] Roll  {ROLL_COST}g", True, BLACK)
        self.screen.blit(r_txt, (px + 5, y + 7))

        # LUCK UPGRADE button
        luck_col = (100, 180, 255) if self.currency >= self.luck_cost else (80, 80, 80)
        pygame.draw.rect(self.screen, luck_col, (px + 145, y, 135, 32), border_radius=6)
        l_txt = self.font_sm.render(f"[G] Luck Lv{self.luck_level+1}", True, BLACK)
        l_txt2= self.font_sm.render(f"{self.luck_cost}g", True, BLACK)
        self.screen.blit(l_txt,  (px + 150, y + 4))
        self.screen.blit(l_txt2, (px + 150, y + 18))
        y += 42

        # Gacha rates display
        label("— Gacha Rates —", GRAY)
        bonus = self.luck_level * 0.015
        for rarity, base_rate in BASE_RATES.items():
            if rarity in ("Rare","Epic","Legendary"):
                adj = base_rate + bonus * {"Rare":1.5,"Epic":1.2,"Legendary":0.8}[rarity]
            else:
                adj = max(0.05, base_rate - bonus * (3 if rarity=="Common" else 1))
            # normalise roughly
            pct = adj / (sum(BASE_RATES.values()) + 0.001) * 100
            rc  = RARITY_COLORS[rarity]
            txt = self.font_sm.render(f"{rarity:<12} {pct:.1f}%", True, rc)
            self.screen.blit(txt, (px, y))
            y += 18
        y += 6

        # Inventory
        label("— Inventory (click to select) —", GRAY)
        ix = px
        iy = y
        for i, tname in enumerate(self.inventory):
            tpl  = TOWER_TEMPLATES[tname]
            col  = tpl[4]
            rc   = RARITY_COLORS[tpl[0]]
            selected = (i == self.selected_inv)
            bg_col = (60, 60, 80) if not selected else (100, 100, 160)
            pygame.draw.rect(self.screen, bg_col,  (ix, iy, 50, 50), border_radius=5)
            pygame.draw.rect(self.screen, rc,       (ix, iy, 50, 50), 2, border_radius=5)
            draw_shape(self.screen, col, tpl[5], ix + 25, iy + 25, 12)
            nm = self.font_sm.render(tname[:6], True, WHITE)
            self.screen.blit(nm, (ix, iy + 36))
            ix += 56
            if ix > SCREEN_W - 60:
                ix = px
                iy += 60
        y = max(y + 60, iy + 70)

        # Selected placed tower info
        if self.selected_tower is not None and self.selected_tower < len(self.towers):
            t = self.towers[self.selected_tower]
            y = max(y, SCREEN_H - 145)
            pygame.draw.rect(self.screen, (40, 45, 60), (px, y, 285, 135), border_radius=6)
            pygame.draw.rect(self.screen, RARITY_COLORS[t.rarity], (px, y, 285, 135), 2, border_radius=6)
            self.screen.blit(self.font_md.render(t.name, True, RARITY_COLORS[t.rarity]), (px + 6, y + 6))
            self.screen.blit(self.font_sm.render(f"Rarity: {t.rarity}",     True, WHITE), (px + 6, y + 28))
            self.screen.blit(self.font_sm.render(f"Level:  {t.level}",      True, WHITE), (px + 6, y + 46))
            self.screen.blit(self.font_sm.render(f"Damage: {t.damage}",     True, WHITE), (px + 6, y + 64))
            self.screen.blit(self.font_sm.render(f"Range:  {t.range_px}px", True, WHITE), (px + 6, y + 82))
            uc = t.upgrade_cost()
            ub_col = (100, 220, 100) if self.currency >= uc else (100, 100, 100)
            pygame.draw.rect(self.screen, ub_col, (px + 6, y + 102, 180, 26), border_radius=5)
            self.screen.blit(self.font_sm.render(f"[U] Upgrade  {uc}g", True, BLACK), (px + 10, y + 108))

        # Controls reminder at bottom
        ctrl = self.font_sm.render("[R]Roll  [G]Luck  [U]Upgrade  Click=Place/Select", True, (120,120,120))
        self.screen.blit(ctrl, (px, SCREEN_H - 20))

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        msg   = "GAME OVER" if self.game_over else "VICTORY!"
        color = (220, 60, 60) if self.game_over else (255, 220, 50)
        big   = pygame.font.SysFont("consolas", 64, bold=True)
        med   = pygame.font.SysFont("consolas", 24)

        s1 = big.render(msg, True, color)
        s2 = med.render("Press SPACE to restart or ESC to quit", True, WHITE)
        self.screen.blit(s1, (SCREEN_W // 2 - s1.get_width() // 2, SCREEN_H // 2 - 60))
        self.screen.blit(s2, (SCREEN_W // 2 - s2.get_width() // 2, SCREEN_H // 2 + 20))

    # ── INPUT ─────────────────────────────────────────────────────────────────

    def handle_input(self, event):
        if self.game_over or self.victory:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.reset()
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()

            elif event.key == pygame.K_r:
                # Roll for a tower
                if self.currency >= ROLL_COST:
                    self.currency -= ROLL_COST
                    tname = gacha_roll(self.luck_level)
                    self.inventory.append(tname)
                    self.popup = RollPopup(tname)
                    for _ in range(20):
                        self.particles.append(Particle(
                            SCREEN_W - 170, 80,
                            RARITY_COLORS[TOWER_TEMPLATES[tname][0]]
                        ))

            elif event.key == pygame.K_g:
                # Upgrade luck
                if self.currency >= self.luck_cost:
                    self.currency  -= self.luck_cost
                    self.luck_level += 1
                    self.luck_cost  = int(self.luck_cost * 1.8)

            elif event.key == pygame.K_u:
                # Upgrade selected placed tower
                if self.selected_tower is not None and self.selected_tower < len(self.towers):
                    t  = self.towers[self.selected_tower]
                    uc = t.upgrade_cost()
                    if self.currency >= uc:
                        self.currency -= uc
                        t.upgrade()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Click on game area (left of panel)
            if mx < SCREEN_W - 300:
                gx = mx // GRID
                gy = my // GRID
                # Place tower from inventory
                if self.selected_inv is not None:
                    if (gx, gy) not in PATH_CELLS:
                        occupied = any(t.gx == gx and t.gy == gy for t in self.towers)
                        if not occupied:
                            tname = self.inventory.pop(self.selected_inv)
                            self.towers.append(Tower(tname, gx, gy))
                            self.selected_inv  = None
                            self.selected_tower = len(self.towers) - 1
                else:
                    # Select placed tower
                    self.selected_tower = None
                    for i, t in enumerate(self.towers):
                        if abs(t.px - mx) < GRID // 2 and abs(t.py - my) < GRID // 2:
                            self.selected_tower = i
                            break
            else:
                # Click on inventory panel
                px = SCREEN_W - 295
                # inventory item clicks — compute positions
                ix, iy = px, 300   # approximate start of inventory (adjust as needed)
                for i in range(len(self.inventory)):
                    col_i = i % 5
                    row_i = i // 5
                    item_x = px + col_i * 56
                    item_y = 300 + row_i * 60
                    if item_x <= mx <= item_x + 50 and item_y <= my <= item_y + 50:
                        self.selected_inv = i if self.selected_inv != i else None
                        self.selected_tower = None
                        break

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def update(self):
        if self.game_over or self.victory:
            return

        self.tick += 1
        self.spawner.update(self.enemies)

        # victory: survive 15 waves
        if self.spawner.wave > 15 and not self.spawner.active and self.spawner.between:
            if len(self.enemies) == 0:
                self.victory = True

        for e in self.enemies[:]:
            e.update()
            if e.reached_end:
                self.base_hp -= 1
                self.enemies.remove(e)
                if self.base_hp <= 0:
                    self.game_over = True
            elif not e.alive:
                self.currency += e.reward
                for _ in range(12):
                    self.particles.append(Particle(int(e.px), int(e.py), e.color))
                self.enemies.remove(e)

        for t in self.towers:
            t.update(self.enemies, self.projectiles)

        for p in self.projectiles[:]:
            p.update()
            if not p.alive:
                self.projectiles.remove(p)

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        if self.popup:
            self.popup.update()
            if self.popup.timer <= 0:
                self.popup = None

    # ── DRAW ──────────────────────────────────────────────────────────────────

    def draw(self):
        self.draw_map()

        for t in self.towers:
            t.draw(self.screen, selected=(self.selected_tower == self.towers.index(t)))

        for e in self.enemies:
            e.draw(self.screen)

        for p in self.projectiles:
            p.draw(self.screen)

        for p in self.particles:
            p.draw(self.screen)

        # placement ghost
        if self.selected_inv is not None:
            mx, my = pygame.mouse.get_pos()
            if mx < SCREEN_W - 300:
                gx, gy = mx // GRID, my // GRID
                cx, cy = gx * GRID + GRID // 2, gy * GRID + GRID // 2
                valid = (gx, gy) not in PATH_CELLS and not any(t.gx == gx and t.gy == gy for t in self.towers)
                col = (100, 255, 100, 120) if valid else (255, 80, 80, 120)
                ghost = pygame.Surface((GRID, GRID), pygame.SRCALPHA)
                ghost.fill(col)
                self.screen.blit(ghost, (gx * GRID, gy * GRID))

        self.draw_ui()

        if self.popup:
            self.popup.draw(self.screen)

        if self.game_over or self.victory:
            self.draw_game_over()

        pygame.display.flip()

    # ── MAIN LOOP ─────────────────────────────────────────────────────────────

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                self.handle_input(event)

            self.update()
            self.draw()
            self.clock.tick(FPS)


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    Game().run()
