"""
games/pong/pong_game.py — Gesture Pong implementation.
"""

import pygame
import random
import cv2
import numpy as np
from typing import List, Optional, Tuple, Any, Dict

from games.base_game import BaseGame
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    PADDLE_WIDTH, PADDLE_HEIGHT,
    BALL_RADIUS, AI_SPEED, WINNING_SCORE,
    BALL_INITIAL_SPEED, BALL_SPEED_INCREASE, BALL_TIME_SPEED_INCREASE,
    PONG_BG, PONG_BALL_COLOR, PONG_PLAYER_COLOR, PONG_AI_COLOR,
    PONG_NET_COLOR, PONG_SCORE_COLOR, WHITE
)

class PongGame(BaseGame):
    def __init__(self, screen, clock, tracker):
        super().__init__(screen, clock, tracker)
        self.reset()
        self.font = pygame.font.SysFont("Arial", 32)
        self.large_font = pygame.font.SysFont("Arial", 64)

    def reset(self):
        self._score = 0
        self.ai_score = 0
        self._is_over = False
        self.exit_requested = False
        self.winner = None
        
        # Player paddle
        self.player_rect = pygame.Rect(50, SCREEN_HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
        # AI paddle
        self.ai_rect = pygame.Rect(SCREEN_WIDTH - 50 - PADDLE_WIDTH, SCREEN_HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
        
        self.reset_ball()

    def reset_ball(self):
        self.ball_pos = [SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2]
        # Start at 45 degrees (approx)
        angle = random.choice([-1, 1]) * 45
        speed = BALL_INITIAL_SPEED
        self.ball_vel = [
            speed * (1 if random.random() > 0.5 else -1),
            speed * (1 if random.random() > 0.5 else -1)
        ]

    def update(self, hand_data: Optional[List[Dict[str, Any]]]) -> None:
        if self._is_over:
            return

        # Track which paddles are being controlled by hands this frame
        right_hand_active = False
        
        if hand_data:
            # Sort hands by X-coordinate of palm center for robust side-mapping
            hands_with_pos = []
            for hand in hand_data:
                cx, cy = self.tracker.get_palm_center(hand["landmarks"])
                hands_with_pos.append((cx, cy, hand))
            
            # Sort by cx (left to right)
            hands_with_pos.sort(key=lambda item: item[0])

            if len(hands_with_pos) == 1:
                cx, cy, _ = hands_with_pos[0]
                # If only one hand, decide which paddle it controls based on screen side
                if cx < SCREEN_WIDTH // 2:
                    self.player_rect.centery = cy
                else:
                    self.ai_rect.centery = cy
                    right_hand_active = True
            else:
                # Two or more hands: left-most controls player, right-most controls AI/P2
                self.player_rect.centery = hands_with_pos[0][1]
                self.ai_rect.centery = hands_with_pos[-1][1]
                right_hand_active = True

        # Clamp paddles
        self.player_rect.top = max(0, min(SCREEN_HEIGHT - PADDLE_HEIGHT, self.player_rect.top))
        self.ai_rect.top = max(0, min(SCREEN_HEIGHT - PADDLE_HEIGHT, self.ai_rect.top))

        # AI tracking (only if no right hand is controlling the paddle)
        if not right_hand_active:
            if self.ball_pos[1] < self.ai_rect.centery:
                self.ai_rect.y -= min(AI_SPEED, self.ai_rect.centery - self.ball_pos[1])
            elif self.ball_pos[1] > self.ai_rect.centery:
                self.ai_rect.y += min(AI_SPEED, self.ball_pos[1] - self.ai_rect.centery)
            self.ai_rect.top = max(0, min(SCREEN_HEIGHT - PADDLE_HEIGHT, self.ai_rect.top))

        # Ball movement
        self.ball_pos[0] += self.ball_vel[0]
        self.ball_pos[1] += self.ball_vel[1]

        # Wall collisions (top/bottom)
        if self.ball_pos[1] - BALL_RADIUS <= 0 or self.ball_pos[1] + BALL_RADIUS >= SCREEN_HEIGHT:
            self.ball_vel[1] *= -1

        # Continuous speed increase over time
        self.ball_vel[0] *= BALL_TIME_SPEED_INCREASE
        self.ball_vel[1] *= BALL_TIME_SPEED_INCREASE

        # Paddle collisions
        ball_rect = pygame.Rect(self.ball_pos[0] - BALL_RADIUS, self.ball_pos[1] - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2)
        
        if ball_rect.colliderect(self.player_rect):
            self.ball_pos[0] = self.player_rect.right + BALL_RADIUS
            self.ball_vel[0] *= -1
            # Increase speed
            self.ball_vel[0] *= BALL_SPEED_INCREASE
            self.ball_vel[1] *= BALL_SPEED_INCREASE

        if ball_rect.colliderect(self.ai_rect):
            self.ball_pos[0] = self.ai_rect.left - BALL_RADIUS
            self.ball_vel[0] *= -1
            # Increase speed
            self.ball_vel[0] *= BALL_SPEED_INCREASE
            self.ball_vel[1] *= BALL_SPEED_INCREASE

        # Score update
        if self.ball_pos[0] < 0:
            self.ai_score += 1
            # TODO: add sound on score
            self.check_game_over()
            if not self._is_over:
                self.reset_ball()
        elif self.ball_pos[0] > SCREEN_WIDTH:
            self._score += 1
            # TODO: add sound on score
            self.check_game_over()
            if not self._is_over:
                self.reset_ball()

    def check_game_over(self):
        if self._score >= WINNING_SCORE:
            self._is_over = True
            self.winner = "Player"
        elif self.ai_score >= WINNING_SCORE:
            self._is_over = True
            self.winner = "AI"

    def draw(self, screen):
        screen.fill(PONG_BG)
        
        # Draw net
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.rect(screen, PONG_NET_COLOR, (SCREEN_WIDTH // 2 - 2, y + 10, 4, 20))

        # Draw paddles
        pygame.draw.rect(screen, PONG_PLAYER_COLOR, self.player_rect, border_radius=5)
        pygame.draw.rect(screen, PONG_AI_COLOR, self.ai_rect, border_radius=5)

        # Draw ball
        pygame.draw.circle(screen, PONG_BALL_COLOR, (int(self.ball_pos[0]), int(self.ball_pos[1])), BALL_RADIUS)

        # Draw score
        player_score_surf = self.font.render(str(self._score), True, PONG_SCORE_COLOR)
        ai_score_surf = self.font.render(str(self.ai_score), True, PONG_SCORE_COLOR)
        screen.blit(player_score_surf, (SCREEN_WIDTH // 4, 50))
        screen.blit(ai_score_surf, (3 * SCREEN_WIDTH // 4, 50))

        # Draw winner text
        if self._is_over:
            winner_text = f"{self.winner} Wins!"
            winner_surf = self.large_font.render(winner_text, True, WHITE)
            screen.blit(winner_surf, (SCREEN_WIDTH // 2 - winner_surf.get_width() // 2, SCREEN_HEIGHT // 2 - winner_surf.get_height() // 2))

    def get_overlay_surface(self, frame):
        """Creates a surface with hand landmarks from the camera frame."""
        overlay_frame = np.zeros((frame.shape[0], frame.shape[1], 3), dtype=np.uint8)
        self.tracker.draw_landmarks_on_frame(overlay_frame)
        # Convert BGR to RGB
        overlay_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
        # Rotate and flip for Pygame (OpenCV is H,W,C for Pygame it's W,H,C after swapaxes)
        overlay_surf = pygame.surfarray.make_surface(overlay_frame.swapaxes(0, 1))
        overlay_surf = pygame.transform.scale(overlay_surf, (320, 180)) # Scale down for PiP
        return overlay_surf
