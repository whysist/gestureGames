"""
games/flappy/flappy_game.py — Gesture Flappy Bird implementation.
"""

import pygame
import random
import cv2
import numpy as np
from typing import List, Optional, Tuple, Any, Dict

from games.base_game import BaseGame
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    FLAPPY_GRAVITY, FLAPPY_FLAP_POWER, FLAPPY_PIPE_SPEED,
    FLAPPY_INITIAL_GAP, FLAPPY_MIN_GAP, FLAPPY_GAP_REDUCTION,
    FLAPPY_PIPE_WIDTH, FLAPPY_PIPE_SPACING, FLAPPY_BIRD_SIZE,
    FLAPPY_FLAP_THRESHOLD,
    WHITE, BLACK, NEON_CYAN, NEON_MAGENTA, NEON_GREEN, NEON_YELLOW
)

class Bird:
    def __init__(self):
        self.size = FLAPPY_BIRD_SIZE
        self.reset()

    def reset(self):
        self.x = 200
        self.y = SCREEN_HEIGHT // 2
        self.vel = 0
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)

    def flap(self):
        self.vel = FLAPPY_FLAP_POWER

    def update(self):
        self.vel += FLAPPY_GRAVITY
        self.y += self.vel
        self.rect.y = int(self.y)

    def draw(self, screen: pygame.Surface):
        # Draw bird as a neon yellow circle with an eye
        pygame.draw.circle(screen, NEON_YELLOW, (int(self.x + self.size/2), int(self.y + self.size/2)), self.size//2)
        # Eye
        pygame.draw.circle(screen, BLACK, (int(self.x + self.size * 0.7), int(self.y + self.size * 0.3)), 4)
        # Wing
        pygame.draw.ellipse(screen, WHITE, (int(self.x + self.size * 0.1), int(self.y + self.size * 0.5), 15, 10))

class Pipe:
    def __init__(self, x: int, gap: int):
        self.x = x
        self.width = FLAPPY_PIPE_WIDTH
        self.gap = gap
        self.top_h = random.randint(100, SCREEN_HEIGHT - self.gap - 100)
        self.passed = False
        self.update_rects()

    def update_rects(self):
        self.top_rect = pygame.Rect(self.x, 0, self.width, self.top_h)
        self.bot_rect = pygame.Rect(self.x, self.top_h + self.gap, self.width, SCREEN_HEIGHT - (self.top_h + self.gap))

    def update(self):
        self.x -= FLAPPY_PIPE_SPEED
        self.update_rects()

    def draw(self, screen: pygame.Surface):
        # Draw neon green pipes
        pygame.draw.rect(screen, NEON_GREEN, self.top_rect, border_radius=5)
        pygame.draw.rect(screen, NEON_GREEN, self.bot_rect, border_radius=5)
        # Border
        pygame.draw.rect(screen, WHITE, self.top_rect, 2, border_radius=5)
        pygame.draw.rect(screen, WHITE, self.bot_rect, 2, border_radius=5)

class FlappyGame(BaseGame):
    def __init__(self, screen, clock, tracker):
        super().__init__(screen, clock, tracker)
        self.font = pygame.font.SysFont("Outfit", 48, bold=True)
        self.large_font = pygame.font.SysFont("Outfit", 90, bold=True)
        self.reset()

    def reset(self):
        self._score = 0
        self._is_over = False
        self.exit_requested = False
        self.bird = Bird()
        self.pipes: List[Pipe] = []
        self.spawn_pipe(SCREEN_WIDTH + 100)
        self.last_hand_y = None
        self.game_started = False
        self.countdown_start = 0

    def spawn_pipe(self, x: int):
        # Gap gets smaller as score increases
        current_gap = max(FLAPPY_MIN_GAP, FLAPPY_INITIAL_GAP - int(self._score * FLAPPY_GAP_REDUCTION))
        self.pipes.append(Pipe(x, current_gap))

    def update(self, hand_data: Optional[List[Dict[str, Any]]]) -> None:
        if self._is_over:
            return

        # Gesture logic for flapping
        if hand_data:
            # Use the first hand detected
            landmarks = hand_data[0]["landmarks"]
            cx, cy = self.tracker.get_palm_center(landmarks)
            
            if self.last_hand_y is not None:
                dy = cy - self.last_hand_y
                if dy > FLAPPY_FLAP_THRESHOLD:
                    self.bird.flap()
                    self.game_started = True
            
            self.last_hand_y = cy
        else:
            self.last_hand_y = None

        if not self.game_started:
            return

        # Bird update
        self.bird.update()

        # Pipe update
        for pipe in self.pipes:
            pipe.update()
            
            # Score check
            if not pipe.passed and pipe.x + pipe.width < self.bird.x:
                pipe.passed = True
                self._score += 1
                
        # Remove off-screen pipes
        if self.pipes and self.pipes[0].x < -FLAPPY_PIPE_WIDTH:
            self.pipes.pop(0)

        # Spawn new pipes
        if self.pipes[-1].x < SCREEN_WIDTH - FLAPPY_PIPE_SPACING:
            self.spawn_pipe(SCREEN_WIDTH)

        # Collision detection
        for pipe in self.pipes:
            if self.bird.rect.colliderect(pipe.top_rect) or self.bird.rect.colliderect(pipe.bot_rect):
                self._is_over = True

        # Bound check
        if self.bird.y < 0 or self.bird.y + self.bird.size > SCREEN_HEIGHT:
            self._is_over = True

    def draw(self, screen: pygame.Surface):
        # Sky blue background
        screen.fill((20, 20, 40))
        
        # Draw pipes
        for pipe in self.pipes:
            pipe.draw(screen)
            
        # Draw bird
        self.bird.draw(screen)

        # Draw Score
        score_surf = self.font.render(str(self._score), True, WHITE)
        screen.blit(score_surf, (SCREEN_WIDTH // 2 - score_surf.get_width() // 2, 50))

        if not self.game_started:
            msg = "Move Hand DOWN to Flap!"
            msg_surf = self.font.render(msg, True, NEON_CYAN)
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, SCREEN_HEIGHT // 2 + 100))

        if self._is_over:
            msg = "Game Over!"
            msg_surf = self.large_font.render(msg, True, NEON_MAGENTA)
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, SCREEN_HEIGHT // 2 - msg_surf.get_height() // 2))
            
            final_score = f"Score: {self._score}"
            final_surf = self.font.render(final_score, True, WHITE)
            screen.blit(final_surf, (SCREEN_WIDTH // 2 - final_surf.get_width() // 2, SCREEN_HEIGHT // 2 + 100))

    def get_overlay_surface(self, frame):
        """Creates a surface with hand landmarks from the camera frame."""
        overlay_frame = np.zeros((frame.shape[0], frame.shape[1], 3), dtype=np.uint8)
        self.tracker.draw_landmarks_on_frame(overlay_frame)
        overlay_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
        overlay_surf = pygame.surfarray.make_surface(overlay_frame.swapaxes(0, 1))
        overlay_surf = pygame.transform.scale(overlay_surf, (320, 180))
        return overlay_surf
