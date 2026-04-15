"""
ui/hub.py — Main menu / game selector screen.
"""

import pygame
from typing import List, Dict, Any

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    HUB_BG, HUB_CARD_BG, HUB_CARD_BORDER,
    HUB_TITLE_COLOR, HUB_READY_COLOR, HUB_SOON_COLOR, HUB_ACCENT,
    WHITE, BLACK, LIGHT_GRAY
)

class Hub:
    def __init__(self, screen):
        self.screen = screen
        self.title_font = pygame.font.SysFont("Arial", 72, bold=True)
        self.name_font = pygame.font.SysFont("Arial", 28, bold=True)
        self.badge_font = pygame.font.SysFont("Arial", 20, bold=True)
        
        # Game registration
        self.games = [
            {"name": "Gesture Pong",   "id": "pong",    "key": pygame.K_1},
            {"name": "Point Selfie",   "id": "selfie",  "key": pygame.K_2},
            {"name": "Subway Surfer",  "id": "surfer",  "key": pygame.K_3},
            {"name": "Brick Breaker",  "id": "breakout", "key": pygame.K_4},
        ]
        
        self.exit_click_rect = pygame.Rect(SCREEN_WIDTH - 60, 20, 40, 40)

    def draw(self):
        self.screen.fill(HUB_BG)
        
        # Title
        title_surf = self.title_font.render("GestureArcade", True, HUB_TITLE_COLOR)
        self.screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 60))
        
        # Grid settings (Single Row)
        card_w, card_h = 260, 280
        gap = 40
        cols = 4
        start_x = (SCREEN_WIDTH - (cols * card_w + (cols - 1) * gap)) // 2
        start_y = 220

        for i, game in enumerate(self.games):
            x = start_x + i * (card_w + gap)
            y = start_y
            
            # Card highlight (outer glow effect)
            outer_rect = pygame.Rect(x - 4, y - 4, card_w + 8, card_h + 8)
            pygame.draw.rect(self.screen, HUB_CARD_BORDER, outer_rect, width=1, border_radius=20)

            # Card background
            card_rect = pygame.Rect(x, y, card_w, card_h)
            pygame.draw.rect(self.screen, HUB_CARD_BG, card_rect, border_radius=18)
            
            # Interactive Key indicator pill
            pill_rect = pygame.Rect(x + card_w // 2 - 40, y - 20, 80, 40)
            pygame.draw.rect(self.screen, HUB_ACCENT, pill_rect, border_radius=20)
            key_text = f"{i+1}"
            key_surf = self.badge_font.render(key_text, True, BLACK)
            self.screen.blit(key_surf, (pill_rect.centerx - key_surf.get_width() // 2, pill_rect.centery - key_surf.get_height() // 2))

            # Game Name
            name_surf = self.name_font.render(game["name"], True, WHITE)
            self.screen.blit(name_surf, (x + card_w // 2 - name_surf.get_width() // 2, y + 80))
            
            # Motivational / Instruction text (Psychological retention)
            hint_font = pygame.font.SysFont("Arial", 18)
            hints = [
                "Test your reflexes",
                "Wondered how your face looks to a robot ?",
                "Swipe to survive",
                "Classic brick action"
            ]
            hint_surf = hint_font.render(hints[i], True, LIGHT_GRAY)
            self.screen.blit(hint_surf, (x + card_w // 2 - hint_surf.get_width() // 2, y + 130))

            # Status Button / Badge
            badge_surf = self.badge_font.render("READY PLAYER", True, HUB_READY_COLOR)
            badge_bg_rect = pygame.Rect(x + 30, y + card_h - 70, card_w - 60, 40)
            pygame.draw.rect(self.screen, (30, 40, 60), badge_bg_rect, border_radius=12)
            pygame.draw.rect(self.screen, HUB_READY_COLOR, badge_bg_rect, width=1, border_radius=12)
            
            self.screen.blit(badge_surf, (badge_bg_rect.centerx - badge_surf.get_width() // 2, badge_bg_rect.centery - badge_surf.get_height() // 2))

        # Close Button
        pygame.draw.circle(self.screen, (200, 50, 50), self.exit_click_rect.center, 20)
        x_surf = self.badge_font.render("X", True, WHITE)
        self.screen.blit(x_surf, (self.exit_click_rect.centerx - x_surf.get_width()//2,
                                  self.exit_click_rect.centery - x_surf.get_height()//2))

    def get_game_selection(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                return self.games[0]["id"]
            if event.key == pygame.K_2:
                return self.games[1]["id"]
            if event.key == pygame.K_3:
                return self.games[2]["id"]
            if event.key == pygame.K_4:
                return self.games[3]["id"]
        return None
