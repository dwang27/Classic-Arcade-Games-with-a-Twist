import pygame
import sys
import random

# Initialize Pygame
pygame.init()

# Screen settings
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("2 Player Pong")
clock = pygame.time.Clock()

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 50, 50)
BLUE = (50, 150, 255)

# Game variables
PADDLE_WIDTH = 15
PADDLE_HEIGHT = 100
BALL_SIZE = 15
PADDLE_SPEED = 8
BALL_SPEED = 6

# Fonts
font = pygame.font.SysFont("Arial", 50)
small_font = pygame.font.SysFont("Arial", 30)

class Paddle:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, PADDLE_WIDTH, PADDLE_HEIGHT)
        self.speed = PADDLE_SPEED

    def move_up(self):
        self.rect.y -= self.speed
        if self.rect.top < 0:
            self.rect.top = 0

    def move_down(self):
        self.rect.y += self.speed
        if self.rect.bottom > HEIGHT:
            self.rect.bottom = HEIGHT

    def draw(self):
        pygame.draw.rect(screen, WHITE, self.rect)


class Ball:
    def __init__(self):
        self.rect = pygame.Rect(WIDTH//2 - BALL_SIZE//2, HEIGHT//2 - BALL_SIZE//2, BALL_SIZE, BALL_SIZE)
        self.reset()

    def reset(self):
        self.rect.center = (WIDTH//2, HEIGHT//2)
        # Random initial direction (avoid straight horizontal)
        angle = random.choice([-45, 45, -30, 30, 60, -60])
        self.speed_x = BALL_SPEED * (1 if random.random() > 0.5 else -1)
        self.speed_y = BALL_SPEED * (angle / 45)

    def move(self):
        self.rect.x += self.speed_x
        self.rect.y += self.speed_y

    def draw(self):
        pygame.draw.rect(screen, WHITE, self.rect)

    def bounce(self, paddle=None):
        if paddle:
            # Increase speed slightly on paddle hit + angle based on hit position
            self.speed_x *= -1.05
            # Change vertical speed based on where it hits the paddle
            hit_pos = (self.rect.centery - paddle.rect.centery) / (PADDLE_HEIGHT / 2)
            self.speed_y = hit_pos * BALL_SPEED * 1.2
        else:
            # Wall bounce
            self.speed_y *= -1


# Create objects
player1 = Paddle(30, HEIGHT//2 - PADDLE_HEIGHT//2)   # Left
player2 = Paddle(WIDTH - 30 - PADDLE_WIDTH, HEIGHT//2 - PADDLE_HEIGHT//2)  # Right
ball = Ball()

score1 = 0
score2 = 0
winning_score = 7

# Game loop
running = True
game_over = False
winner = None

while running:
    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if game_over and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:  # Press R to restart
                score1 = 0
                score2 = 0
                game_over = False
                winner = None
                ball.reset()

    if not game_over:
        # Player movement
        keys = pygame.key.get_pressed()
       
        # Player 1 (W/S)
        if keys[pygame.K_w]:
            player1.move_up()
        if keys[pygame.K_s]:
            player1.move_down()

        # Player 2 (Arrow keys)
        if keys[pygame.K_UP]:
            player2.move_up()
        if keys[pygame.K_DOWN]:
            player2.move_down()

        # Ball movement
        ball.move()

        # Ball collisions with walls (top/bottom)
        if ball.rect.top <= 0 or ball.rect.bottom >= HEIGHT:
            ball.bounce()

        # Ball collisions with paddles
        if ball.rect.colliderect(player1.rect) and ball.speed_x < 0:
            ball.bounce(player1)
        if ball.rect.colliderect(player2.rect) and ball.speed_x > 0:
            ball.bounce(player2)

        # Scoring
        if ball.rect.left <= 0:
            score2 += 1
            ball.reset()
        if ball.rect.right >= WIDTH:
            score1 += 1
            ball.reset()

        # Check for winner
        if score1 >= winning_score:
            game_over = True
            winner = "Player 1 (Blue Side)"
        elif score2 >= winning_score:
            game_over = True
            winner = "Player 2 (Red Side)"

    # Drawing
    screen.fill(BLACK)

    # Draw center line
    pygame.draw.aaline(screen, WHITE, (WIDTH//2, 0), (WIDTH//2, HEIGHT))

    # Draw objects
    player1.draw()
    player2.draw()
    ball.draw()

    # Draw scores
    score_text1 = font.render(str(score1), True, BLUE)
    score_text2 = font.render(str(score2), True, RED)
    screen.blit(score_text1, (WIDTH//4, 30))
    screen.blit(score_text2, (3*WIDTH//4 - score_text2.get_width(), 30))

    # Instructions
    if not game_over:
        instr = small_font.render("Player 1: W / S     Player 2: ↑ / ↓", True, (150, 150, 150))
        screen.blit(instr, (WIDTH//2 - instr.get_width()//2, HEIGHT - 40))

    # Game Over screen
    if game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))

        game_over_text = font.render("GAME OVER", True, WHITE)
        winner_text = font.render(winner + " WINS!", True, WHITE)
        restart_text = small_font.render("Press R to Play Again", True, WHITE)

        screen.blit(game_over_text, (WIDTH//2 - game_over_text.get_width()//2, HEIGHT//2 - 100))
        screen.blit(winner_text, (WIDTH//2 - winner_text.get_width()//2, HEIGHT//2))
        screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 80))

    pygame.display.flip()

pygame.quit()
sys.exit()

