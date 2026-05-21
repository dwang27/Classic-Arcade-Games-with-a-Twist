"""
GACHA TOWER DEFENSE (pygame)

HOW TO RUN:
    pip install pygame
    python gacha_tower_defense.py

CONTROLS:
    Left-click  → Place tower / Select tower / Click inventory
    R key       → Roll for a tower (costs gold)
    U key       → Upgrade selected placed tower (max level 5)
    G key       → Upgrade gacha luck (max level 5)
    S key       → Sell selected tower or inventory item (50% refund)
    ESC         → Return to menu
"""

import pygame, random, math, sys
pygame.mixer.init()
pygame.mixer.music.load("/Users/derekhuang/Gacha_Tower_Defence/Classic-Arcade-Game-With-a-Twist/C418 - Sweden - Minecraft Volume Alpha.mp3")
pygame.mixer.music.play(-1)  # -1 makes it loop infinitely
pygame.mixer.music.set_volume(0.5)  # Set volume to 50% (adjust 0.0-1.0 as needed)

# Info
SCREEN_W, SCREEN_H = 1160, 720
FPS       = 60
GRID      = 40
MAX_WAVES = 10
SELL_REF  = 0.50   # sell refund fraction
MAX_TOWER_LEVEL = 5
MAX_LUCK  = 5

WHITE  = (255,255,255);  BLACK  = (0,0,0);     GRAY  = (180,180,180)
GRASS  = (55,95,50);     PATH_C = (210,180,140); PANEL = (22,28,38)

RARITY_COLORS = {
    "Common":    (160, 160, 160),
    "Uncommon":  ( 60, 200,  80),
    "Rare":      ( 60, 120, 255),
    "Epic":      (160,  50, 220),
    "Legendary": (255, 160,  30),
    "Secret":    (255,  50, 100),   # dragon egg — hot pink/red
}
BASE_RATES = {"Common":0.50,"Uncommon":0.25,"Rare":0.15,"Epic":0.07,"Legendary":0.03}
# Secret has a fixed tiny chance added on top — not part of the normalised pool
SECRET_RATE = 0.005   # 0.5% flat, unaffected by luck
ROLL_COST  = 80

# Path
PATH_WPS = [(0,2),(4,2),(4,6),(8,6),(8,2),(13,2),(13,10),(4,10),(4,13),(19,13)]
PIXEL_PATH = [(x*GRID+GRID//2, y*GRID+GRID//2) for x,y in PATH_WPS]

def _path_cells():
    cells = set()
    for i in range(len(PATH_WPS)-1):
        x0,y0 = PATH_WPS[i]; x1,y1 = PATH_WPS[i+1]
        if x0==x1:
            for r in range(min(y0,y1),max(y0,y1)+1): cells.add((x0,r))
        else:
            for c in range(min(x0,x1),max(x0,x1)+1): cells.add((c,y0))
    return cells
PATH_CELLS = _path_cells()

# Tower Templates (rarity, dmg, range, fire_rate, color, base cost, img)
TOWER_T = {
    # Common — dirt & wood
    "Dirt Tower":      ("Common",    7,  105, 58, (139,  90,  43),  80, "dirt.png"),
    "Wood Tower":      ("Common",   10,  110, 55, (170, 130,  70),  80, "wood.png"),

    # Uncommon — stone & copper
    "Stone Tower":     ("Uncommon", 20,  135, 48, (130, 130, 130), 160, "stone.png"),
    "Copper Tower":    ("Uncommon", 24,  130, 50, (196, 127,  75), 160, "copper.png"),

    # Rare — iron & gold
    "Iron Tower":      ("Rare",     34,  150, 42, (210, 210, 210), 240, "iron.png"),
    "Gold Tower":      ("Rare",     38,  145, 38, (255, 215,   0), 240, "gold.png"),

    # Epic — emerald & lapis
    "Emerald Tower":   ("Epic",     55,  168, 30, ( 20, 200,  80), 320, "emerald.png"),
    "Lapis Tower":     ("Epic",     58,  155, 32, ( 30,  80, 200), 320, "lapis.png"),

    # Legendary — diamond & netherite
    "Diamond Tower":   ("Legendary", 88, 198, 25, ( 90, 215, 255), 400, "diamond.png"),
    "Netherite Tower": ("Legendary",115, 182, 20, ( 70,  60,  70), 400, "netherite.png"),

    # SECRET - dragon egg
    "Dragon Egg Tower":("Secret",   250, 240, 12, (220,  40,  90), 999, "dragon_egg.png"),
}

# Enemy Types
ENEMY_T = [
    {"name":"Normal",   "hp":80,    "spd":1.6, "rew":10,       "sz":12, "wave":1,  "dmg":1, "img":"zombie.png"},
    {"name":"Speedy",   "hp":45,    "spd":3.4, "rew":14,       "sz":10, "wave":2,  "dmg":1, "img":"spider.png"},
    {"name":"Tank",     "hp":320,   "spd":0.9, "rew":25,       "sz":18, "wave":3,  "dmg":2, "img":"warden.png"},
    {"name":"Mini Boss","hp":700,   "spd":1.1, "rew":50,       "sz":22, "wave":4,  "dmg":3, "img":"wither.png"},
    {"name":"Boss",     "hp":1800,  "spd":0.7, "rew":120,      "sz":28, "wave":6, "dmg":5, "img":"dragon.png"},
    {"name":"Final",    "hp":50000, "spd":0.2, "rew":50000000, "sz":50, "wave":10,           "img":"storm.png"},
]
DIFF = {
    "easy":  {"hp":20,"hp_m":0.80,"rew_m":1.20,"lbl":"EASY",  "col":(60,200,80)},
    "normal":{"hp":15,"hp_m":1.00,"rew_m":1.00,"lbl":"NORMAL","col":(80,140,255)},
    "hard":  {"hp":10,"hp_m":1.20,"rew_m":0.80,"lbl":"HARD",  "col":(220,60,60)},
}

# Rarity 
def lerp_col(a,b,t): return tuple(int(a[i]+(b[i]-a[i])*t) for i in range(3))

def gacha_roll(luck=0):
    # check secret pull first (flat 0.5 %, luck slightly boosts it)
    secret_chance = SECRET_RATE + luck * 0.001
    if random.random() < secret_chance:
        return "Dragon Egg Tower"

    bonus = luck * 0.015
    r = dict(BASE_RATES)
    r["Common"]    = max(0.05, r["Common"]    - bonus * 3)
    r["Uncommon"]  = max(0.05, r["Uncommon"]  - bonus)
    r["Rare"]      += bonus * 1.5
    r["Epic"]      += bonus * 1.2
    r["Legendary"] += bonus * 0.8
    tot = sum(r.values()); r = {k:v/tot for k,v in r.items()}
    roll=random.random(); cum=0; chosen="Common"
    for rar,p in r.items():
        cum+=p
        if roll<cum: chosen=rar; break
    return random.choice([n for n,t in TOWER_T.items() if t[0]==chosen])

# Tower
class Tower:
    def __init__(self, name, gx, gy):
        t = TOWER_T[name]
        self.name     = name
        self.rarity   = t[0]
        self.dmg      = t[1]
        self.rng      = t[2]
        self.rate     = t[3]
        self.col      = t[4]
        self.base_cost= t[5]

        try:
            self.img = pygame.image.load(f"textures/{t[6]}").convert_alpha()
            self.img = pygame.transform.scale(self.img, (32, 32))
        except Exception:
            # fallback: coloured square if texture missing
            self.img = pygame.Surface((32, 32), pygame.SRCALPHA)
            self.img.fill((*t[4], 200))

        self.gx = gx; self.gy = gy
        self.px = gx*GRID+GRID//2
        self.py = gy*GRID+GRID//2
        self.cd = 0; self.level = 1; self.spent = t[5]
        self.flash = 0; self.target = None

    # Level Cap 
    def upgrade_cost(self):
        if self.level >= MAX_TOWER_LEVEL:
            return None
        return 60 * self.level

    def sell_val(self):
        return int(self.spent * SELL_REF)

    def upgrade(self):
        if self.level >= MAX_TOWER_LEVEL:
            return
        self.spent += self.upgrade_cost()
        self.level += 1
        self.dmg   = int(self.dmg  * 1.4)
        self.rng   = int(self.rng  * 1.1)
        self.rate  = max(8, int(self.rate * 0.85))

    def update(self, enemies, projectiles):
        if self.cd   > 0: self.cd   -= 1
        if self.flash> 0: self.flash -= 1
        best = None; bp = -1
        for e in enemies:
            d = math.hypot(e.px-self.px, e.py-self.py)
            if d <= self.rng and e.prog > bp:
                best = e; bp = e.prog
        self.target = best
        if best and self.cd == 0:
            projectiles.append(Projectile(self.px, self.py, best, self.dmg, self.col))
            self.cd = self.rate; self.flash = 6

    def draw(self, surf, sel=False):
        sz = GRID//2-4
        if sel:
            r  = self.rng
            rs = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            rs.fill((255,255,255,22))
            pygame.draw.rect(rs,(255,255,255,80),(0,0,r*2,r*2),1)
            surf.blit(rs,(self.px-r, self.py-r))
            pygame.draw.rect(surf,(255,255,100),(self.px-sz-6,self.py-sz-6,(sz+6)*2,(sz+6)*2),2)

        surf.blit(self.img,(self.px-sz, self.py-sz))
        rc = RARITY_COLORS[self.rarity]
        pygame.draw.rect(surf,rc,(self.px-sz-3,self.py-sz-3,(sz+3)*2,(sz+3)*2),2)

        # rainbow border for secret rarity
        if self.rarity == "Secret":
            t_val = (pygame.time.get_ticks() % 1200) / 1200
            pulse = lerp_col((255,50,100),(255,200,50), abs(math.sin(t_val*math.pi)))
            pygame.draw.rect(surf,pulse,(self.px-sz-5,self.py-sz-5,(sz+5)*2,(sz+5)*2),3)

        if self.level > 1:
            f  = pygame.font.SysFont("consolas",11,bold=True)
            lb = f.render(f"L{self.level}",True,WHITE)
            surf.blit(lb,(self.px-lb.get_width()//2, self.py-sz-14))


# Enemy
class Enemy:
    def __init__(self, tidx, wave, hp_m=1.0, rew_m=1.0):
        t  = ENEMY_T[tidx]
        ws = 1.0 + 0.05*(wave-1)
        self.name   = t["name"]
        self.hp     = int(t["hp"]*ws*hp_m); self.max_hp = self.hp
        self.spd    = t["spd"]; self.rew = int(t["rew"]*rew_m)
        self.sz     = t["sz"];  self.dmg = t.get("dmg",1)
        try:
            self.img = pygame.image.load(f"textures/{t['img']}").convert_alpha()
            w,h      = self.img.get_size()
            scale    = (self.sz*2)/h
            self.img = pygame.transform.scale(self.img,(int(w*scale),int(h*scale)))
        except Exception:
            self.img = pygame.Surface((self.sz*2,self.sz*2),pygame.SRCALPHA)
            self.img.fill((200,50,50,200))
        self.wp  = 0; self.px,self.py = PIXEL_PATH[0]; self.prog = 0.0
        self.alive = True; self.done = False

    def update(self):
        if self.wp+1 >= len(PIXEL_PATH): self.done=True; return
        tx,ty = PIXEL_PATH[self.wp+1]; dx,dy = tx-self.px, ty-self.py
        dist  = math.hypot(dx,dy)
        if dist < self.spd:
            self.px,self.py = tx,ty; self.wp+=1; self.prog+=dist
        else:
            self.px+=dx/dist*self.spd; self.py+=dy/dist*self.spd; self.prog+=self.spd

    def hit(self,d):
        self.hp-=d
        if self.hp<=0: self.alive=False

    def draw(self,surf):
        s = self.sz
        surf.blit(self.img,(int(self.px)-self.img.get_width()//2,
                             int(self.py)-self.img.get_height()//2))
        bw  = s*2; rat = max(0,self.hp/self.max_hp)
        pygame.draw.rect(surf,(120,0,0),(int(self.px)-s,int(self.py)-s-8,bw,5))
        pygame.draw.rect(surf,(0,220,60),(int(self.px)-s,int(self.py)-s-8,int(bw*rat),5))


# Projectile 
class Projectile:
    def __init__(self,x,y,target,dmg,col):
        self.x=float(x); self.y=float(y); self.target=target
        self.dmg=dmg; self.col=col; self.spd=8.0; self.alive=True

    def update(self):
        if not self.target.alive: self.alive=False; return
        dx=self.target.px-self.x; dy=self.target.py-self.y
        dist=math.hypot(dx,dy)
        if dist<self.spd: self.target.hit(self.dmg); self.alive=False
        else: self.x+=dx/dist*self.spd; self.y+=dy/dist*self.spd

    def draw(self,surf):
        pygame.draw.rect(surf,self.col,(int(self.x)-4,int(self.y)-4,8,8))
        pygame.draw.rect(surf,WHITE,   (int(self.x)-2,int(self.y)-2,4,4))


# Spawner 
class Spawner:
    def __init__(self,hp_m=1.0,rew_m=1.0):
        self.wave=0; self.spawned=0; self.queue=[]; self.tick=0
        self.active=False; self.between=True; self.btimer=0
        self.hp_m=hp_m; self.rew_m=rew_m

    def _build(self):
        q=[]; n=8+self.wave*3
        avail=[i for i,e in enumerate(ENEMY_T) if self.wave>=e["wave"] and i!=5]
        if self.wave>=5  and self.wave%5==0: q.append(4); n-=1
        if self.wave>=3  and self.wave%3==0: q.append(3); n-=1
        if self.wave==10: q.append(5); n-=1
        for _ in range(max(0,n)): q.append(random.choice(avail))
        random.shuffle(q); return q

    def start(self):
        self.wave+=1; self.queue=self._build(); self.spawned=0
        self.active=True; self.between=False; self.tick=0

    def update(self,enemies):
        if self.between:
            self.btimer-=1
            if self.btimer<=0: self.start()
            return
        if not self.active: return
        self.tick-=1
        if self.tick<=0 and self.spawned<len(self.queue):
            enemies.append(Enemy(self.queue[self.spawned],self.wave,self.hp_m,self.rew_m))
            self.spawned+=1; self.tick=max(18,60-self.wave*2)
        if self.spawned>=len(self.queue) and len(enemies)==0:
            self.active=False; self.between=True; self.btimer=FPS*5

    def status(self):
        if self.between:
            s=max(0,self.btimer//FPS)
            if self.wave==0: return f"Starting in {s}s..."
            return f"Wave {self.wave}/{MAX_WAVES} done! Next in {s}s"
        return f"Wave {self.wave}/{MAX_WAVES}  {self.spawned}/{len(self.queue)}"


# Menu
class Menu:
    def __init__(self,screen):
        self.screen=screen; self.choice=None; self.hov=None
        self.fl=pygame.font.SysFont("consolas",32,bold=True)
        self.fm=pygame.font.SysFont("consolas",17)
        self.fs=pygame.font.SysFont("consolas",14)
        self.modes=[
            {"k":"easy",  "lbl":"EASY",  "col":(60,200,80),
             "desc":["+20% gold earned","-20% enemy HP","20 base health"]},
            {"k":"normal","lbl":"NORMAL","col":(80,140,255),
             "desc":["Standard gold","Standard HP","15 base health"]},
            {"k":"hard",  "lbl":"HARD",  "col":(220,60,60),
             "desc":["-20% gold earned","+20% enemy HP","10 base health"]},
        ]

    def _rect(self,i):
        cw,ch=250,230; gap=38
        tw=len(self.modes)*cw+(len(self.modes)-1)*gap
        sx=(SCREEN_W-tw)//2
        return sx+i*(cw+gap), SCREEN_H//2-ch//2+50, cw, ch

    def handle(self,ev):
        if ev.type==pygame.MOUSEMOTION:
            self.hov=None; mx,my=ev.pos
            for i,m in enumerate(self.modes):
                rx,ry,rw,rh=self._rect(i)
                if rx<=mx<=rx+rw and ry<=my<=ry+rh: self.hov=m["k"]
        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
            mx,my=ev.pos
            for i,m in enumerate(self.modes):
                rx,ry,rw,rh=self._rect(i)
                if rx<=mx<=rx+rw and ry<=my<=ry+rh: self.choice=m["k"]
        if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE:
            pygame.quit(); sys.exit()

    def draw(self):
        self.screen.fill((16,20,28))
        t=self.fl.render("GACHA TOWER DEFENSE",True,(255,220,50))
        self.screen.blit(t,(SCREEN_W//2-t.get_width()//2,70))
        s=self.fm.render("Choose a difficulty",True,(130,145,170))
        self.screen.blit(s,(SCREEN_W//2-s.get_width()//2,118))
        for i,m in enumerate(self.modes):
            rx,ry,rw,rh=self._rect(i)
            bg=(45,55,78) if self.hov==m["k"] else (30,36,50)
            pygame.draw.rect(self.screen,bg,(rx,ry,rw,rh),border_radius=10)
            pygame.draw.rect(self.screen,m["col"],(rx,ry,rw,rh),2,border_radius=10)
            lb=self.fl.render(m["lbl"],True,m["col"])
            self.screen.blit(lb,(rx+rw//2-lb.get_width()//2,ry+18))
            for j,d in enumerate(m["desc"]):
                ds=self.fs.render(d,True,(185,195,215))
                self.screen.blit(ds,(rx+rw//2-ds.get_width()//2,ry+100+j*22))
        h=self.fs.render("ESC to quit",True,(70,85,110))
        self.screen.blit(h,(SCREEN_W//2-h.get_width()//2,SCREEN_H-35))
        pygame.display.flip()


# Game
class Game:
    def __init__(self,diff,screen,clock):
        self.diff=diff; self.screen=screen; self.clock=clock
        self.ds=DIFF[diff]
        self.fbig=pygame.font.SysFont("consolas",26,bold=True)
        self.flg =pygame.font.SysFont("consolas",19,bold=True)
        self.fmd =pygame.font.SysFont("consolas",15)
        self.fsm =pygame.font.SysFont("consolas",13)
        self.reset()

    def reset(self):
        ds=self.ds
        self.towers=[]; self.enemies=[]; self.projs=[]
        self.gold=250; self.hp=ds["hp"]; self.max_hp=ds["hp"]
        self.luck=0; self.luck_cost=150
        self.inv=[]; self.sel_inv=None; self.sel_tow=None
        self.inv_rects=[]
        self.spawner=Spawner(ds["hp_m"],ds["rew_m"])
        self.spawner.btimer=FPS*4
        self.over=False; self.win=False; self.tick=0

    # Draw
    def draw_map(self):
        self.screen.fill(GRASS)
        if len(PIXEL_PATH)>1:
            pygame.draw.lines(self.screen,PATH_C,False,PIXEL_PATH,GRID-4)
        for pt in PIXEL_PATH:
            pygame.draw.circle(self.screen,(200,165,120),pt,GRID//2-2)
        pygame.draw.circle(self.screen,(50,200,50),PIXEL_PATH[0],10)
        pygame.draw.circle(self.screen,(220,50,50),PIXEL_PATH[-1],10)
        pygame.draw.rect(self.screen,PANEL,(SCREEN_W-310,0,310,SCREEN_H))

    def draw_ui(self):
        px=SCREEN_W-305; y=8
        def lb(txt,col=WHITE,big=False):
            nonlocal y
            f=self.flg if big else self.fmd
            s=f.render(txt,True,col)
            self.screen.blit(s,(px,y)); y+=s.get_height()+3

        dc=self.ds["col"]; dl=self.ds["lbl"]
        ds=self.fsm.render(dl,True,dc); self.screen.blit(ds,(px,y)); y+=ds.get_height()+2

        lb("GACHA TOWER DEFENSE",(255,220,50),big=True); y+=2

        bw=292; rat=self.hp/self.max_hp
        pygame.draw.rect(self.screen,(100,0,0),(px,y,bw,18))
        pygame.draw.rect(self.screen,(220,50,50),(px,y,int(bw*rat),18))
        self.screen.blit(self.fsm.render(f"♥ {self.hp}/{self.max_hp}",True,WHITE),(px+5,y+2))
        y+=24

        lb(f"Gold: {self.gold}")
        lb(self.spawner.status(),(180,200,255))
        y+=4

        # Roll Button
        rc2=(255,200,50) if self.gold>=ROLL_COST else (70,70,70)
        pygame.draw.rect(self.screen,rc2,(px,y,140,29),border_radius=5)
        self.screen.blit(self.fsm.render(f"[R] Roll {ROLL_COST}g",True,BLACK),(px+5,y+8))

        # Luck Button (greyed out and labelled MAXED at cap)
        if self.luck >= MAX_LUCK:
            pygame.draw.rect(self.screen,(50,50,50),(px+148,y,148,29),border_radius=5)
            self.screen.blit(self.fsm.render("[G] Luck MAXED",True,(140,140,140)),(px+152,y+8))
        else:
            lc=(100,180,255) if self.gold>=self.luck_cost else (65,65,65)
            pygame.draw.rect(self.screen,lc,(px+148,y,148,29),border_radius=5)
            self.screen.blit(self.fsm.render(f"[G] Luck{self.luck+1} {self.luck_cost}g",True,BLACK),(px+152,y+8))
        y+=35

        # Gacha Rates
        lb("— Rates —",GRAY)
        bonus=self.luck*0.015
        mat_hint={
            "Common":   "(Dirt/Wood)",
            "Uncommon": "(Stone/Copper)",
            "Rare":     "(Iron/Gold)",
            "Epic":     "(Emerald/Lapis)",
            "Legendary":"(Diamond/Netherite)",
        }
        for rar,br in BASE_RATES.items():
            if rar in ("Rare","Epic","Legendary"):
                adj=br+bonus*{"Rare":1.5,"Epic":1.2,"Legendary":0.8}[rar]
            else:
                adj=max(0.05,br-bonus*(3 if rar=="Common" else 1))
            pct=adj/(sum(BASE_RATES.values())+0.001)*100
            self.screen.blit(self.fsm.render(f"{rar:<10}{pct:.1f}%",True,RARITY_COLORS[rar]),(px,y))
            y+=16
            hint=self.fsm.render(mat_hint[rar],True,tuple(max(0,c-60) for c in RARITY_COLORS[rar]))
            self.screen.blit(hint,(px+8,y)); y+=14

        # Secret Rate (with special colour effect)
        t_val=(pygame.time.get_ticks()%1200)/1200
        sec_col=lerp_col((255,50,100),(255,200,50), abs(math.sin(t_val*math.pi)))
        sec_pct=(SECRET_RATE+self.luck*0.001)*100
        self.screen.blit(self.fsm.render(f"{'Secret':<10}{sec_pct:.2f}%",True,sec_col),(px,y)); y+=16
        self.screen.blit(self.fsm.render("(Dragon Egg)",True,tuple(max(0,c-60) for c in sec_col)),(px+8,y)); y+=14
        y+=4

        # Inventory
        lb("— Inventory —",GRAY)
        inv_y0=y; ix=px
        self.inv_rects=[]
        for i,tn in enumerate(self.inv):
            t=TOWER_T[tn]; rc=RARITY_COLORS[t[0]]
            sel=(i==self.sel_inv)
            bg=(100,100,160) if sel else (52,58,78)
            pygame.draw.rect(self.screen,bg,(ix,y,48,48),border_radius=4)
            pygame.draw.rect(self.screen,rc,(ix,y,48,48),2,border_radius=4)
            # extra border for secret
            if t[0]=="Secret":
                pulse=lerp_col((255,50,100),(255,200,50),abs(math.sin(t_val*math.pi)))
                pygame.draw.rect(self.screen,pulse,(ix-2,y-2,52,52),2,border_radius=5)
            try:
                img=pygame.image.load(f"textures/{t[6]}").convert_alpha()
                img=pygame.transform.scale(img,(24,24))
                self.screen.blit(img,(ix+12,y+12))
            except Exception:
                sq=pygame.Surface((24,24),pygame.SRCALPHA); sq.fill((*t[4],200))
                self.screen.blit(sq,(ix+12,y+12))
            self.inv_rects.append((ix,y,48,48))
            ix+=54
            if ix+48>SCREEN_W-4: ix=px; y+=54
        y=max(inv_y0,y)+54+4

        # Preview for selected inventory item
        if self.sel_inv is not None and self.sel_inv<len(self.inv):
            tn=self.inv[self.sel_inv]; tp=TOWER_T[tn]
            rc=RARITY_COLORS[tp[0]]
            py2=y
            pygame.draw.rect(self.screen,(35,42,58),(px,py2,295,115),border_radius=6)
            pygame.draw.rect(self.screen,rc,(px,py2,295,115),2,border_radius=6)
            self.screen.blit(self.fmd.render(tn,True,rc),(px+6,py2+5))
            for j,(k,v) in enumerate([("Rarity",tp[0]),("Damage",tp[1]),("Range",f"{tp[2]}px"),("Fire rate",f"every {tp[3]} ticks")]):
                self.screen.blit(self.fsm.render(f"{k:<10} {v}",True,WHITE),(px+6,py2+26+j*18))
            sv=int(ROLL_COST*SELL_REF)
            self.screen.blit(self.fsm.render(f"[S] Sell for {sv}g",True,(255,165,50)),(px+6,py2+98))
            y=py2+122

        # Selected placed tower info panel
        if self.sel_tow is not None and self.sel_tow<len(self.towers):
            t=self.towers[self.sel_tow]
            iy2=max(y,SCREEN_H-170)
            pygame.draw.rect(self.screen,(35,42,58),(px,iy2,295,162),border_radius=6)
            pygame.draw.rect(self.screen,RARITY_COLORS[t.rarity],(px,iy2,295,162),2,border_radius=6)
            self.screen.blit(self.fmd.render(t.name,True,RARITY_COLORS[t.rarity]),(px+6,iy2+5))
            for j,(k,v) in enumerate([("Rarity",t.rarity),("Level",f"{t.level}/{MAX_TOWER_LEVEL}"),("Damage",t.dmg),("Range",f"{t.rng}px"),("Fire rate",f"every {t.rate} ticks")]):
                self.screen.blit(self.fsm.render(f"{k:<10} {v}",True,WHITE),(px+6,iy2+26+j*18))

            # Upgrade Button (greyed out when at max level)
            uc = t.upgrade_cost()
            if uc is None:
                pygame.draw.rect(self.screen,(50,50,50),(px+6,iy2+118,140,26),border_radius=5)
                self.screen.blit(self.fsm.render("[U] MAX LEVEL",True,(140,140,140)),(px+10,iy2+125))
            else:
                ubc=(100,220,100) if self.gold>=uc else (75,75,75)
                pygame.draw.rect(self.screen,ubc,(px+6,iy2+118,140,26),border_radius=5)
                self.screen.blit(self.fsm.render(f"[U] Upgrade {uc}g",True,BLACK),(px+10,iy2+125))

            sv=t.sell_val()
            pygame.draw.rect(self.screen,(200,120,30),(px+154,iy2+118,134,26),border_radius=5)
            self.screen.blit(self.fsm.render(f"[S] Sell +{sv}g",True,BLACK),(px+158,iy2+125))

        self.screen.blit(self.fsm.render("[R]Roll [G]Luck [U]Upg [S]Sell [ESC]Menu",True,(90,105,125)),(px,SCREEN_H-18))

    def draw_over(self):
        ov=pygame.Surface((SCREEN_W,SCREEN_H),pygame.SRCALPHA)
        ov.fill((0,0,0,165)); self.screen.blit(ov,(0,0))
        msg="GAME OVER" if self.over else "VICTORY!"
        col=(220,60,60) if self.over else (255,220,50)
        s1=self.fbig.render(msg,True,col)
        s2=self.fmd.render("SPACE = restart   ESC = menu",True,WHITE)
        self.screen.blit(s1,(SCREEN_W//2-s1.get_width()//2,SCREEN_H//2-50))
        self.screen.blit(s2,(SCREEN_W//2-s2.get_width()//2,SCREEN_H//2+20))

    def draw(self):
        self.draw_map()
        for t in self.towers:
            t.draw(self.screen, sel=(self.sel_tow is not None and
                                     self.sel_tow<len(self.towers) and
                                     self.towers[self.sel_tow] is t))
        for e in self.enemies: e.draw(self.screen)
        for p in self.projs:   p.draw(self.screen)

        # Ghost + Tooltip
        if self.sel_inv is not None and self.sel_inv<len(self.inv):
            mx,my=pygame.mouse.get_pos()
            if mx<SCREEN_W-310:
                gx,gy=mx//GRID,my//GRID
                valid=(gx,gy) not in PATH_CELLS and not any(t.gx==gx and t.gy==gy for t in self.towers)
                gc=(100,255,100,90) if valid else (255,80,80,90)
                gh=pygame.Surface((GRID,GRID),pygame.SRCALPHA); gh.fill(gc)
                self.screen.blit(gh,(gx*GRID,gy*GRID))
                tn=self.inv[self.sel_inv]; tp=TOWER_T[tn]
                tlines=[tn,f"DMG {tp[1]}  RNG {tp[2]}px",f"Rate: {tp[3]} ticks"]
                tx2=min(mx+14,SCREEN_W-320-162); ty2=my-10
                tw2=158; th2=len(tlines)*18+10
                pygame.draw.rect(self.screen,(18,22,32),(tx2,ty2,tw2,th2),border_radius=4)
                pygame.draw.rect(self.screen,RARITY_COLORS[tp[0]],(tx2,ty2,tw2,th2),1,border_radius=4)
                for j,ln in enumerate(tlines):
                    c2=RARITY_COLORS[tp[0]] if j==0 else WHITE
                    self.screen.blit(self.fsm.render(ln,True,c2),(tx2+5,ty2+5+j*18))

        self.draw_ui()
        if self.over or self.win: self.draw_over()
        pygame.display.flip()

    # Input
    def handle(self,ev):
        if self.over or self.win:
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_SPACE: self.reset()
                elif ev.key==pygame.K_ESCAPE: return "menu"
            return

        if ev.type==pygame.KEYDOWN:
            k=ev.key
            if k==pygame.K_ESCAPE: return "menu"

            elif k==pygame.K_r:
                if self.gold>=ROLL_COST:
                    self.gold-=ROLL_COST; self.inv.append(gacha_roll(self.luck))

            elif k==pygame.K_g:
                # luck is capped at MAX_LUCK
                if self.luck < MAX_LUCK and self.gold >= self.luck_cost:
                    self.gold -= self.luck_cost
                    self.luck += 1
                    self.luck_cost = int(self.luck_cost * 1.8)

            elif k==pygame.K_u:
                if self.sel_tow is not None and self.sel_tow<len(self.towers):
                    t=self.towers[self.sel_tow]
                    uc=t.upgrade_cost()
                    # uc is None when already at max level
                    if uc is not None and self.gold>=uc:
                        self.gold-=uc; t.upgrade()

            elif k==pygame.K_s:
                if self.sel_tow is not None and self.sel_tow<len(self.towers):
                    self.gold+=self.towers[self.sel_tow].sell_val()
                    self.towers.pop(self.sel_tow); self.sel_tow=None
                elif self.sel_inv is not None and self.sel_inv<len(self.inv):
                    self.gold+=int(ROLL_COST*SELL_REF)
                    self.inv.pop(self.sel_inv); self.sel_inv=None

        elif ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
            mx,my=ev.pos
            if mx<SCREEN_W-310:
                gx,gy=mx//GRID,my//GRID
                if self.sel_inv is not None:
                    if (gx,gy) not in PATH_CELLS and not any(t.gx==gx and t.gy==gy for t in self.towers):
                        tn=self.inv.pop(self.sel_inv)
                        self.towers.append(Tower(tn,gx,gy))
                        self.sel_tow=len(self.towers)-1; self.sel_inv=None
                else:
                    self.sel_tow=None
                    for i,t in enumerate(self.towers):
                        if abs(t.px-mx)<GRID//2 and abs(t.py-my)<GRID//2:
                            self.sel_tow=i; self.sel_inv=None; break
            else:
                for i,(rx,ry,rw,rh) in enumerate(self.inv_rects):
                    if rx<=mx<=rx+rw and ry<=my<=ry+rh:
                        self.sel_inv=i if self.sel_inv!=i else None
                        self.sel_tow=None; break

    # Update
    def update(self):
        if self.over or self.win: return
        self.tick+=1
        self.spawner.update(self.enemies)
        if self.spawner.wave>=MAX_WAVES and not self.spawner.active and self.spawner.between and not self.enemies:
            self.win=True
        for e in self.enemies[:]:
            e.update()
            if e.done:
                self.hp = 0 if e.name=="Final" else self.hp-e.dmg
                self.enemies.remove(e)
                self.over=(self.hp<=0)
            elif not e.alive:
                self.gold+=e.rew; self.enemies.remove(e)
        for t in self.towers: t.update(self.enemies,self.projs)
        for p in self.projs[:]:
            p.update()
            if not p.alive: self.projs.remove(p)

    def run(self):
        while True:
            res=None
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
                r=self.handle(ev)
                if r: res=r
            if res=="menu": return "menu"
            self.update(); self.draw(); self.clock.tick(FPS)


# Main 
def main():
    pygame.init()
    screen=pygame.display.set_mode((SCREEN_W,SCREEN_H), pygame.FULLSCREEN)
    pygame.display.set_caption("Gacha Tower Defense")
    clock=pygame.time.Clock()
    while True:
        menu=Menu(screen)
        while menu.choice is None:
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT: pygame.quit(); sys.exit()
                menu.handle(ev)
            menu.draw(); clock.tick(FPS)
        game=Game(menu.choice,screen,clock)
        game.run()

main()
