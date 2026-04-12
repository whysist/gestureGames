"""
ui/hub.py — Main menu / game selector screen.
"""

import pygame
from typing import List, Dict, Any

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    HUB_BG, HUB_CARD_BG, HUB_CARD_BORDER,
    HUB_TITLE_COLOR, HUB_READY_COLOR, HUB_SOON_COLOR, HUB_ACCENT,
    WHITE, BLACK
)

class Hub:
    def __init__(self, screen):
        self.screen = screen
        self.title_font = pygame.font.SysFont("Arial", 72, bold=True)
        self.name_font = pygame.font.SysFont("Arial", 28, bold=True)
        self.badge_font = pygame.font.SysFont("Arial", 20, bold=True)
        
        # Game registration
        self.games = [
            {"name": "Gesture Pong", "status": "READY", "key": pygame.K_1},
            {"name": "Fruit Ninja", "status": "READY", "key": pygame.K_2},
            {"name": "Point Selfie", "status": "READY", "key": pygame.K_3},
            {"name": "Flappy Bird", "status": "READY", "key": pygame.K_4},
            {"name": "Air Drumming",    "status": "READY", "key": pygame.K_5},
            {"name": "Subway Surfer",   "status": "READY", "key": pygame.K_6},
        ]
        # TODO: register new mini-game here

    def draw(self):
        self.screen.fill(HUB_BG)
        
        # Title
        title_surf = self.title_font.render("GestureArcade", True, HUB_TITLE_COLOR)
        self.screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 60))
        
        # Grid settings
        card_w, card_h = 240, 260
        gap = 30
        cols = 3
        start_x = (SCREEN_WIDTH - (cols * card_w + (cols - 1) * gap)) // 2
        start_y = 180

        for i, game in enumerate(self.games):
            row = i // cols
            col = i % cols
            x = start_x + col * (card_w + gap)
            y = start_y + row * (card_h + gap)
            
            # Card background
            card_rect = pygame.Rect(x, y, card_w, card_h)
            pygame.draw.rect(self.screen, HUB_CARD_BG, card_rect, border_radius=15)
            pygame.draw.rect(self.screen, HUB_CARD_BORDER, card_rect, width=2, border_radius=15)
            
            # Key indicator
            key_text = f"Press {i+1}"
            key_surf = self.badge_font.render(key_text, True, HUB_ACCENT)
            self.screen.blit(key_surf, (x + card_w // 2 - key_surf.get_width() // 2, y + 20))

            # Game Name
            name_surf = self.name_font.render(game["name"], True, WHITE)
            self.screen.blit(name_surf, (x + card_w // 2 - name_surf.get_width() // 2, y + 100))
            
            # Status Badge
            status = game["status"]
            color = HUB_READY_COLOR if status == "READY" else HUB_SOON_COLOR
            badge_surf = self.badge_font.render(status, True, color)
            
            badge_bg_rect = pygame.Rect(x + 40, y + card_h - 60, card_w - 80, 40)
            pygame.draw.rect(self.screen, BLACK, badge_bg_rect, border_radius=10)
            pygame.draw.rect(self.screen, color, badge_bg_rect, width=1, border_radius=10)
            
            self.screen.blit(badge_surf, (x + card_w // 2 - badge_surf.get_width() // 2, y + card_h - 50))

    def get_game_selection(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                return "pong"
            if event.key == pygame.K_2:
                return "ninja"
            if event.key == pygame.K_3:
                return "selfie"
            if event.key == pygame.K_4:
                return "flappy"
            if event.key == pygame.K_5:
                return "drum"
            if event.key == pygame.K_6:
                return "surfer"
        return None
