"""
games/breakout/brick_breaker.py — Gesture-controlled Brick Breaker mini-game.

Move your index finger left/right to control the paddle.
Yellow bricks spawn an extra ball when destroyed.
"""

import pygame
import random
from typing import List, Dict, Any, Optional

from games.base_game import BaseGame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, NEON_CYAN, NEON_MAGENTA, INDEX_TIP


# ---------------- BALL ----------------
class Ball:
    def __init__(self, x, y, speed):
        self.x = x
        self.y = y
        self.dx = random.choice([-1, 1]) * speed
        self.dy = -speed
        self.radius = 8

    def update(self):
        self.x += self.dx
        self.y += self.dy

        # wall bounce
        if self.x - self.radius <= 0:
            self.x = self.radius
            self.dx = abs(self.dx)
        elif self.x + self.radius >= SCREEN_WIDTH:
            self.x = SCREEN_WIDTH - self.radius
            self.dx = -abs(self.dx)

        if self.y - self.radius <= 0:
            self.y = self.radius
            self.dy = abs(self.dy)

    def draw(self, screen):
        pygame.draw.circle(screen, NEON_CYAN, (int(self.x), int(self.y)), self.radius)
        # Glow halo
        glow_surf = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (0, 240, 255, 60), (self.radius * 2, self.radius * 2), self.radius * 2)
        screen.blit(glow_surf, (int(self.x) - self.radius * 2, int(self.y) - self.radius * 2))


# ---------------- BRICK ----------------
class Brick:
    def __init__(self, x, y, w, h, color, special=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = color
        self.alive = True
        self.special = special  # yellow brick → spawns extra ball

    def draw(self, screen):
        if not self.alive:
            return
        pygame.draw.rect(screen, self.color, self.rect, border_radius=4)
        # Inner highlight line
        highlight_rect = pygame.Rect(self.rect.x + 2, self.rect.y + 2, self.rect.width - 4, 4)
        light = tuple(min(255, c + 80) for c in self.color)
        pygame.draw.rect(screen, light, highlight_rect, border_radius=2)
        # Border
        pygame.draw.rect(screen, (0, 0, 0), self.rect, width=1, border_radius=4)


# ---------------- GAME ----------------
class BreakoutGame(BaseGame):
    def __init__(self, screen, clock, tracker):
        super().__init__(screen, clock, tracker)
        self.font = pygame.font.SysFont("Arial", 32, bold=True)
        self.large_font = pygame.font.SysFont("Arial", 70, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 22)
        self.reset()

    def reset(self):
        self._score = 0
        self._is_over = False
        self.exit_requested = False
        self.game_state = "LEVEL_SELECT"

        self.level = None
        self.balls: List[Ball] = []
        self.bricks: List[Brick] = []

        self.paddle_width = 120
        self.paddle_height = 15
        self.paddle_x = SCREEN_WIDTH // 2
        self.paddle_y = SCREEN_HEIGHT - 60

        # Tracks win vs loss for the finish screen
        self._won = False

    # ---------------- LEVEL SETUP ----------------
    def setup_level(self, level: str):
        self.level = level
        self.balls = []
        self.bricks = []
        self._won = False

        if level == "EASY":
            speed = 4
            self.paddle_width = 140
            rows = 3
        elif level == "MEDIUM":
            speed = 6
            self.paddle_width = 110
            rows = 5
        else:  # HARD
            speed = 8
            self.paddle_width = 80
            rows = 6

        self.balls.append(Ball(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, speed))

        # Create bricks
        cols = 8
        brick_w = SCREEN_WIDTH // cols
        brick_h = 30

        # Row colour palette (dark-to-bright progression)
        row_colors = [
            (180, 40,  40),   # deep red
            (200, 90,  20),   # orange
            (180, 160, 20),   # yellow-ish normal
            (40,  140, 200),  # blue
            (120, 40,  200),  # purple
            (40,  180, 80),   # green
        ]

        for r in range(rows):
            base_color = row_colors[r % len(row_colors)]
            for c in range(cols):
                x = c * brick_w
                y = r * brick_h + 50

                # 20 % chance of a special (yellow, multi-ball) brick
                special = random.random() < 0.2
                color = (255, 220, 0) if special else base_color

                self.bricks.append(Brick(x, y, brick_w - 4, brick_h - 4, color, special))

        self.game_state = "PLAYING"

    # ---------------- UPDATE ----------------
    def update(self, hand_data: Optional[List[Dict[str, Any]]]):
        if self.game_state in ("LEVEL_SELECT", "FINISHED"):
            return

        # ---- Paddle control via index-finger tip ----
        if hand_data:
            tip = self.tracker.get_fingertip(hand_data[0]["landmarks"], INDEX_TIP)

            min_x = 100
            max_x = SCREEN_WIDTH - 100
            hand_x = max(min_x, min(max_x, tip[0]))
            mapped_x = int((hand_x - min_x) / (max_x - min_x) * SCREEN_WIDTH)

            # Smooth tracking (70 % old + 30 % new)
            self.paddle_x = int(self.paddle_x * 0.7 + mapped_x * 0.3)
            self.paddle_x = max(self.paddle_width // 2,
                                min(SCREEN_WIDTH - self.paddle_width // 2, self.paddle_x))

        # ---- Update each ball ----
        new_balls: List[Ball] = []
        for ball in self.balls:
            ball.update()

            # Paddle rectangle (centred on paddle_x)
            paddle_rect = pygame.Rect(
                self.paddle_x - self.paddle_width // 2,
                self.paddle_y,
                self.paddle_width,
                self.paddle_height
            )

            # Paddle collision — only when ball is moving downward
            if ball.dy > 0 and paddle_rect.collidepoint(ball.x, ball.y):
                ball.dy = -abs(ball.dy)
                # Add slight angle based on where on paddle the ball hit
                offset = (ball.x - self.paddle_x) / (self.paddle_width / 2)
                ball.dx += offset * 1.5

            # Brick collision
            for brick in self.bricks:
                if not brick.alive:
                    continue
                if brick.rect.collidepoint(ball.x, ball.y):
                    brick.alive = False
                    ball.dy *= -1
                    self._score += 1

                    # Special brick → spawn an extra ball
                    if brick.special:
                        nb = Ball(ball.x, ball.y, abs(ball.dx))
                        new_balls.append(nb)

        self.balls.extend(new_balls)

        # Remove balls that have fallen off screen
        self.balls = [b for b in self.balls if b.y < SCREEN_HEIGHT + b.radius]

        # ---- End conditions ----
        if not self.balls:
            self._won = False
            self.game_state = "FINISHED"
            self._is_over = True

        elif all(not b.alive for b in self.bricks):
            self._won = True
            self.game_state = "FINISHED"
            self._is_over = True

    # ---------------- EVENTS ----------------
    def handle_event(self, event):
        """Called by main.py for game-specific keyboard events."""
        if self.game_state == "LEVEL_SELECT":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    self.setup_level("EASY")
                elif event.key == pygame.K_2:
                    self.setup_level("MEDIUM")
                elif event.key == pygame.K_3:
                    self.setup_level("HARD")

        elif self.game_state == "FINISHED":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.exit_requested = True

    # ---------------- DRAW ----------------
    def draw(self, screen: pygame.Surface):
        screen.fill((10, 10, 25))

        # ── Level Select Screen ──────────────────────────────────────────────
        if self.game_state == "LEVEL_SELECT":
            # Title
            title = self.large_font.render("Brick Breaker", True, NEON_CYAN)
            screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 90))

            sub = self.small_font.render("Move your index finger left/right to control the paddle", True, (160, 160, 200))
            screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 180))

            hint = self.small_font.render("☆ Yellow bricks spawn an extra ball!", True, (255, 220, 0))
            screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 210))

            # Difficulty cards
            difficulties = [
                ("1", "Easy",   "Slow ball · Wide paddle",  NEON_CYAN),
                ("2", "Medium", "Normal ball · Mid paddle",  NEON_MAGENTA),
                ("3", "Hard",   "Fast ball · Narrow paddle", (255, 80, 80)),
            ]
            card_w, card_h = 220, 160
            total_w = len(difficulties) * card_w + (len(difficulties) - 1) * 30
            sx = SCREEN_WIDTH // 2 - total_w // 2

            for i, (key, label, desc, col) in enumerate(difficulties):
                cx = sx + i * (card_w + 30)
                cy = 290
                card_rect = pygame.Rect(cx, cy, card_w, card_h)
                pygame.draw.rect(screen, (18, 22, 42), card_rect, border_radius=14)
                pygame.draw.rect(screen, col, card_rect, width=2, border_radius=14)

                k_surf = self.font.render(f"[{key}]", True, col)
                screen.blit(k_surf, (cx + card_w // 2 - k_surf.get_width() // 2, cy + 16))

                l_surf = self.font.render(label, True, WHITE)
                screen.blit(l_surf, (cx + card_w // 2 - l_surf.get_width() // 2, cy + 60))

                d_surf = self.small_font.render(desc, True, (140, 140, 170))
                screen.blit(d_surf, (cx + card_w // 2 - d_surf.get_width() // 2, cy + 108))

            return

        # ── Playing / Finished Screen ────────────────────────────────────────

        # Draw bricks
        for brick in self.bricks:
            brick.draw(screen)

        # Draw paddle with gradient-ish effect
        paddle_rect = pygame.Rect(
            self.paddle_x - self.paddle_width // 2,
            self.paddle_y,
            self.paddle_width,
            self.paddle_height
        )
        pygame.draw.rect(screen, NEON_MAGENTA, paddle_rect, border_radius=8)
        # Top shine strip
        shine = pygame.Rect(paddle_rect.x + 4, paddle_rect.y + 2, paddle_rect.width - 8, 4)
        pygame.draw.rect(screen, (255, 160, 240), shine, border_radius=4)

        # Draw balls
        for ball in self.balls:
            ball.draw(screen)

        # Score HUD
        score_surf = self.font.render(f"Score: {self._score}", True, WHITE)
        screen.blit(score_surf, (SCREEN_WIDTH - score_surf.get_width() - 20, SCREEN_HEIGHT - 44))

        # Active ball count
        ball_surf = self.small_font.render(f"Balls: {len(self.balls)}", True, NEON_CYAN)
        screen.blit(ball_surf, (20, SCREEN_HEIGHT - 36))

        # ── Finish Overlay ───────────────────────────────────────────────────
        if self.game_state == "FINISHED":
            # Dim overlay
            dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            dim.fill((0, 0, 0, 160))
            screen.blit(dim, (0, 0))

            if self._won:
                msg_text = "You Win!"
                msg_color = NEON_CYAN
            else:
                msg_text = "Game Over"
                msg_color = (255, 80, 80)

            msg = self.large_font.render(msg_text, True, msg_color)
            screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, SCREEN_HEIGHT // 2 - 100))

            sc = self.font.render(f"Final Score: {self._score}", True, WHITE)
            screen.blit(sc, (SCREEN_WIDTH // 2 - sc.get_width() // 2, SCREEN_HEIGHT // 2 - 20))

            sub = self.font.render("Press ESC to Exit", True, NEON_CYAN)
            screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, SCREEN_HEIGHT // 2 + 40))

    # ---------------- OVERLAY (PiP camera) ----------------
    def get_overlay_surface(self, frame):
        import numpy as np
        import cv2
        overlay_frame = np.zeros((frame.shape[0], frame.shape[1], 3), dtype=np.uint8)
        self.tracker.draw_landmarks_on_frame(overlay_frame)
        overlay_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
        overlay_surf = pygame.surfarray.make_surface(overlay_frame.swapaxes(0, 1))
        overlay_surf = pygame.transform.scale(overlay_surf, (320, 180))
        return overlay_surf
