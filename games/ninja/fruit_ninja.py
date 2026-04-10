"""
games/ninja/fruit_ninja.py — Gesture Fruit Ninja implementation.
"""

import pygame
import random
import math
import cv2
import numpy as np
from typing import List, Optional, Tuple, Any, Dict

from games.base_game import BaseGame
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    GRAVITY, FRUIT_MIN_SPEED_Y, FRUIT_MAX_SPEED_Y,
    FRUIT_MIN_SPEED_X, FRUIT_MAX_SPEED_X,
    FRUIT_RADIUS, SLASH_MAX_POINTS, MIN_SLASH_VELOCITY,
    FRUIT_APPLE, FRUIT_ORANGE, FRUIT_WATERMELON,
    WHITE, BLACK, NEON_CYAN, NEON_MAGENTA, INDEX_TIP
)

class Fruit:
    def __init__(self, color: Tuple[int, int, int]):
        self.color = color
        self.radius = FRUIT_RADIUS
        self.reset()

    def reset(self):
        # Spawn at the bottom
        self.x = random.randint(FRUIT_RADIUS * 2, SCREEN_WIDTH - FRUIT_RADIUS * 2)
        self.y = SCREEN_HEIGHT + FRUIT_RADIUS
        
        # Initial velocities
        self.vx = random.uniform(FRUIT_MIN_SPEED_X, FRUIT_MAX_SPEED_X)
        self.vy = random.uniform(FRUIT_MIN_SPEED_Y, FRUIT_MAX_SPEED_Y)
        
        self.is_sliced = False
        self.slice_angle = 0
        self.slice_vx = 0
        self.slice_vy = 0
        self.active = True
        self.spawned = False # Becomes true when it moves on screen

    def update(self):
        if not self.active:
            return

        # Apply gravity
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy

        if self.y < SCREEN_HEIGHT:
            self.spawned = True

        # Deactivate if it falls off screen after being spawned
        if self.spawned and self.y > SCREEN_HEIGHT + FRUIT_RADIUS * 2:
            self.active = False

    def draw(self, screen: pygame.Surface):
        if not self.active:
            return

        cx, cy = int(self.x), int(self.y)
        if not self.is_sliced:
            # Draw whole fruit with more detail
            if self.color == FRUIT_APPLE:
                # Apple body
                pygame.draw.circle(screen, self.color, (cx, cy), self.radius)
                # Stem
                pygame.draw.line(screen, (101, 67, 33), (cx, cy - self.radius + 5), (cx, cy - self.radius - 10), 3)
                # Leaf
                pygame.draw.ellipse(screen, (50, 205, 50), (cx + 2, cy - self.radius - 12, 12, 6))
            elif self.color == FRUIT_ORANGE:
                # Orange body
                pygame.draw.circle(screen, self.color, (cx, cy), self.radius)
                # Texture dimples
                for _ in range(5):
                    dx = random.randint(-self.radius//2, self.radius//2)
                    dy = random.randint(-self.radius//2, self.radius//2)
                    pygame.draw.circle(screen, (255, 140, 0), (cx + dx, cy + dy), 2)
                # Stem point
                pygame.draw.circle(screen, (34, 139, 34), (cx, cy - self.radius + 2), 4)
            elif self.color == FRUIT_WATERMELON:
                # Watermelon body (oval)
                rect = pygame.Rect(cx - self.radius - 10, cy - self.radius, (self.radius + 10) * 2, self.radius * 2)
                pygame.draw.ellipse(screen, self.color, rect)
                # Stripes
                for offset in range(-self.radius, self.radius, 15):
                    pygame.draw.arc(screen, (34, 139, 34), rect.inflate(-10, -5), 0, 3.14, 3)
            else:
                pygame.draw.circle(screen, self.color, (cx, cy), self.radius)

            # Highlight/Shine
            pygame.draw.circle(screen, WHITE, (cx - self.radius // 3, cy - self.radius // 3), self.radius // 5)
        else:
            # Draw two halves moving apart
            # Half 1
            h1_x = self.x - self.radius // 2
            h1_y = self.y
            pygame.draw.circle(screen, self.color, (int(h1_x), int(h1_y)), self.radius, draw_top_left=True, draw_bottom_left=True)
            # Half 2
            h2_x = self.x + self.radius // 2
            h2_y = self.y
            pygame.draw.circle(screen, self.color, (int(h2_x), int(h2_y)), self.radius, draw_top_right=True, draw_bottom_right=True)

    def check_slice(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> bool:
        """Simple line-circle intersection or proximity check for slicing."""
        if self.is_sliced or not self.active:
            return False

        # Distance from point (self.x, self.y) to line segment (p1, p2)
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        if dx == 0 and dy == 0:
            return False

        t = ((self.x - p1[0]) * dx + (self.y - p1[1]) * dy) / (dx*dx + dy*dy)
        t = max(0, min(1, t))
        
        closest_x = p1[0] + t * dx
        closest_y = p1[1] + t * dy
        
        dist_sq = (self.x - closest_x)**2 + (self.y - closest_y)**2
        
        if dist_sq < (self.radius + 10)**2:
            # Check velocity of the slash
            slash_dist = math.sqrt(dx*dx + dy*dy)
            if slash_dist > MIN_SLASH_VELOCITY:
                self.is_sliced = True
                return True
        return False

class Slash:
    def __init__(self, color: Tuple[int, int, int]):
        self.points: List[Tuple[int, int]] = []
        self.color = color

    def update(self, pos: Optional[Tuple[int, int]]):
        if pos:
            self.points.append(pos)
        else:
            if self.points:
                self.points.pop(0)
        
        if len(self.points) > SLASH_MAX_POINTS:
            self.points.pop(0)

    def draw(self, screen: pygame.Surface):
        if len(self.points) < 2:
            return

        # Draw a tapering trail
        for i in range(len(self.points) - 1):
            p1 = self.points[i]
            p2 = self.points[i+1]
            
            # Width grows towards the head (end of list)
            width = int((i + 1) / len(self.points) * 10) + 1
            
            # Fade out older segments
            alpha = int((i + 1) / len(self.points) * 255)
            color = list(self.color)
            
            # Pygame doesn't support alpha in draw.line directly easily on main surface
            # We use a shortcut: just draw multiple lines or a polygon
            pygame.draw.line(screen, self.color, p1, p2, width)

class FruitNinjaGame(BaseGame):
    def __init__(self, screen, clock, tracker):
        super().__init__(screen, clock, tracker)
        self.font = pygame.font.SysFont("Outfit", 36, bold=True)
        self.large_font = pygame.font.SysFont("Outfit", 90, bold=True)
        self.reset()

    def reset(self):
        self._score = 0
        self._is_over = False
        self.exit_requested = False
        self.fruits: List[Fruit] = []
        self.slashes: Dict[int, Slash] = {} # hand_id -> Slash
        
        # Game States: "COUNTDOWN", "PLAYING", "FINISHED"
        self.game_state = "COUNTDOWN"
        self.countdown_start = pygame.time.get_ticks()
        self.countdown_seconds = 3
        
        # Decide how many fruits to spawn
        self.total_fruits = random.randint(10, 20)
        self.fruits_spawned = 0
        self.spawn_timer = 0
        
        # INITIAL_SPAWN_INTERVAL is now much higher (e.g., 80 frames ~ 1.3s)
        self.base_spawn_interval = 80 
        self.current_spawn_interval = self.base_spawn_interval
        
        # To make it less mechanical, we add jitter
        self.next_spawn_delay = self.base_spawn_interval + random.randint(-15, 15)

    def update(self, hand_data: Optional[List[Dict[str, Any]]]) -> None:
        if self._is_over:
            # Brief pause at the end handled in main.py loop but we keep state clean
            return

        # ── State: COUNTDOWN ──────────────────────────────────────────────────
        if self.game_state == "COUNTDOWN":
            elapsed = (pygame.time.get_ticks() - self.countdown_start) / 1000
            if elapsed >= self.countdown_seconds:
                self.game_state = "PLAYING"
            # We still update slashes during countdown so player can see their hands
            self._update_slashes(hand_data)
            return

        # ── State: PLAYING ────────────────────────────────────────────────────
        # 1. Update existing fruits
        for fruit in self.fruits:
            fruit.update()

        # 2. Spawn new fruits
        if self.fruits_spawned < self.total_fruits:
            self.spawn_timer += 1
            if self.spawn_timer >= self.next_spawn_delay:
                color = random.choice([FRUIT_APPLE, FRUIT_ORANGE, FRUIT_WATERMELON])
                self.fruits.append(Fruit(color))
                self.fruits_spawned += 1
                self.spawn_timer = 0
                
                # Gradually speed up: reduce interval by 10% each time, but min 25 frames
                self.current_spawn_interval = max(25, int(self.current_spawn_interval * 0.92))
                # Add jitter for next spawn
                self.next_spawn_delay = self.current_spawn_interval + random.randint(-10, 10)

        # 3. Handle Slashes and Collisions
        self._update_slashes(hand_data)

        # 4. Check for game completion
        if self.fruits_spawned >= self.total_fruits:
            # Check if all fruits are inactive and off screen
            if all(not f.active for f in self.fruits):
                self._is_over = True
                self.game_state = "FINISHED"

    def _update_slashes(self, hand_data: Optional[List[Dict[str, Any]]]):
        active_hand_ids = []
        if hand_data:
            for hand in hand_data:
                hand_id = hand["id"]
                active_hand_ids.append(hand_id)
                landmarks = hand["landmarks"]
                tip_pos = self.tracker.get_fingertip(landmarks, INDEX_TIP)
                
                if hand_id not in self.slashes:
                    self.slashes[hand_id] = Slash(NEON_CYAN if i == 0 else NEON_MAGENTA)
                
                slash = self.slashes[hand_id]
                old_pos = slash.points[-1] if slash.points else None
                slash.update(tip_pos)
                
                # Only check collisions if we are in PLAYING state
                if self.game_state == "PLAYING" and old_pos:
                    for fruit in self.fruits:
                        if fruit.check_slice(old_pos, tip_pos):
                            self._score += 1

        # Cleanup slashes for hands that disappeared
        for hand_id in list(self.slashes.keys()):
            if hand_id not in active_hand_ids:
                self.slashes[hand_id].update(None)
                if not self.slashes[hand_id].points:
                    del self.slashes[hand_id]

    def draw(self, screen: pygame.Surface):
        # Premium dark background
        screen.fill((8, 8, 15))
        
        # Draw fruits
        for fruit in self.fruits:
            fruit.draw(screen)
            
        # Draw slashes
        for slash in self.slashes.values():
            slash.draw(screen)

        # Draw UI
        if self.game_state != "COUNTDOWN":
            score_text = f"Score: {self._score}"
            score_surf = self.font.render(score_text, True, WHITE)
            screen.blit(score_surf, (30, 30))
            
            remaining = self.total_fruits - self.fruits_spawned
            active_count = sum(1 for f in self.fruits if f.active and not f.is_sliced)
            fruits_text = f"Remaining: {remaining + active_count}"
            fruits_surf = self.font.render(fruits_text, True, NEON_CYAN)
            screen.blit(fruits_surf, (SCREEN_WIDTH - fruits_surf.get_width() - 30, 30))

        # ── Overlay State Render ──────────────────────────────────────────────
        if self.game_state == "COUNTDOWN":
            elapsed = (pygame.time.get_ticks() - self.countdown_start) / 1000
            time_left = max(0, self.countdown_seconds - elapsed)
            
            if time_left > 0.5:
                num_text = str(int(math.ceil(time_left)))
                color = NEON_CYAN
            else:
                num_text = "GO!"
                color = NEON_CYAN
                
            num_surf = self.large_font.render(num_text, True, color)
            # Add a slight "throb" / pulse effect based on fractional part
            scale = 1.0 + (math.ceil(time_left) - time_left) * 0.3
            if scale > 1.0:
                num_surf = pygame.transform.rotozoom(num_surf, 0, scale)
                
            screen.blit(num_surf, (SCREEN_WIDTH // 2 - num_surf.get_width() // 2, SCREEN_HEIGHT // 2 - num_surf.get_height() // 2))

        elif self.game_state == "FINISHED":
            msg = "Round Complete!"
            msg_surf = self.large_font.render(msg, True, WHITE)
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, SCREEN_HEIGHT // 2 - msg_surf.get_height() // 2))
            
            final_score_text = f"Final Score: {self._score}"
            final_surf = self.font.render(final_score_text, True, NEON_CYAN)
            screen.blit(final_surf, (SCREEN_WIDTH // 2 - final_surf.get_width() // 2, SCREEN_HEIGHT // 2 + 100))

    def get_overlay_surface(self, frame):
        """Creates a surface with hand landmarks from the camera frame."""
        overlay_frame = np.zeros((frame.shape[0], frame.shape[1], 3), dtype=np.uint8)
        self.tracker.draw_landmarks_on_frame(overlay_frame)
        overlay_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
        overlay_surf = pygame.surfarray.make_surface(overlay_frame.swapaxes(0, 1))
        overlay_surf = pygame.transform.scale(overlay_surf, (320, 180))
        return overlay_surf
