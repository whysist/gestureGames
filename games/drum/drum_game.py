"""
games/drum/drum_game.py — Gesture Air Drumming implementation.
"""

import pygame
import random
import cv2
import numpy as np
from typing import List, Optional, Tuple, Any, Dict

from games.base_game import BaseGame
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    DRUM_LANE_COUNT, DRUM_TILE_SPEED, DRUM_HIT_THRESHOLD,
    DRUM_LANE_WIDTH, DRUM_TILE_HEIGHT, DRUM_HIT_ZONE_Y,
    WHITE, BLACK, NEON_CYAN, NEON_MAGENTA, NEON_GREEN, NEON_YELLOW
)

class DrumTile:
    def __init__(self, lane: int):
        self.lane = lane
        self.w = DRUM_LANE_WIDTH - 20
        self.h = DRUM_TILE_HEIGHT
        self.x = lane * DRUM_LANE_WIDTH + 10
        self.y = -self.h
        self.active = True
        self.hit = False

    def update(self):
        self.y += DRUM_TILE_SPEED
        if self.y > SCREEN_HEIGHT:
            self.active = False
            return False # Missed
        return True

    def draw(self, screen: pygame.Surface):
        color = NEON_GREEN if not self.hit else (200, 200, 200)
        rect = pygame.Rect(self.x, self.y, self.w, self.h)
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, WHITE, rect, width=2, border_radius=8)

class DrumGame(BaseGame):
    def __init__(self, screen, clock, tracker):
        super().__init__(screen, clock, tracker)
        self.font = pygame.font.SysFont("Outfit", 36, bold=True)
        self.large_font = pygame.font.SysFont("Outfit", 80, bold=True)
        self.reset()

    def reset(self):
        self._score = 0
        self._is_over = False
        self.exit_requested = False
        self.tiles: List[DrumTile] = []
        self.spawn_timer = 0
        self.spawn_interval = 60 # frames
        
        # Track hand velocities
        self.last_hand_y = {} # hand_id -> last_y

    def update(self, hand_data: Optional[List[Dict[str, Any]]]) -> None:
        if self._is_over:
            return

        # 1. Update tiles
        for tile in self.tiles:
            if not tile.update():
                if not tile.hit:
                    self._is_over = True # Missed tile ends game
        
        self.tiles = [t for t in self.tiles if t.active]

        # 2. Spawn tiles
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_interval:
            lane = random.randint(0, DRUM_LANE_COUNT - 1)
            self.tiles.append(DrumTile(lane))
            self.spawn_timer = 0
            # Gradually speed up
            self.spawn_interval = max(30, self.spawn_interval - 1)

        # 3. Gesture Detection (Hits)
        current_hand_ids = []
        if hand_data:
            for i, hand in enumerate(hand_data):
                hand_id = hand["label"] + str(i) # Simple ID
                current_hand_ids.append(hand_id)
                landmarks = hand["landmarks"]
                cx, cy = self.tracker.get_palm_center(landmarks)
                
                if hand_id in self.last_hand_y:
                    dy = cy - self.last_hand_y[hand_id]
                    
                    # Check for "Hit" (Downward strike)
                    if dy > DRUM_HIT_THRESHOLD:
                        lane = cx // DRUM_LANE_WIDTH
                        self.check_hit(lane, cy)
                
                self.last_hand_y[hand_id] = cy
        
        # Cleanup old hand tracking
        self.last_hand_y = {hid: y for hid, y in self.last_hand_y.items() if hid in current_hand_ids}

    def check_hit(self, lane: int, y: int):
        # A hit is valid if there's a tile in the lane near the hit zone
        for tile in self.tiles:
            if not tile.hit and tile.lane == lane:
                # Check if tile is within hit zone reach
                dist = abs(tile.y - DRUM_HIT_ZONE_Y)
                if dist < 100: # Forgiving hit window
                    tile.hit = True
                    self._score += 1
                    return

    def draw(self, screen: pygame.Surface):
        screen.fill((10, 10, 25)) # Dark blue
        
        # Draw Lanes
        for i in range(DRUM_LANE_COUNT):
            x = i * DRUM_LANE_WIDTH
            pygame.draw.line(screen, (40, 40, 80), (x, 0), (x, SCREEN_HEIGHT), 1)
        
        # Draw Hit Zone line
        pygame.draw.line(screen, NEON_CYAN, (0, DRUM_HIT_ZONE_Y), (SCREEN_WIDTH, DRUM_HIT_ZONE_Y), 2)
        
        # Draw Tiles
        for tile in self.tiles:
            tile.draw(screen)
            
        # Draw Score
        score_surf = self.font.render(f"Score: {self._score}", True, WHITE)
        screen.blit(score_surf, (SCREEN_WIDTH - 200, 30))

        if self._is_over:
            msg = "GAME OVER"
            msg_surf = self.large_font.render(msg, True, NEON_MAGENTA)
            screen.blit(msg_surf, (SCREEN_WIDTH // 2 - msg_surf.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
            
            final_msg = f"Final Score: {self._score}"
            final_surf = self.font.render(final_msg, True, WHITE)
            screen.blit(final_surf, (SCREEN_WIDTH // 2 - final_surf.get_width() // 2, SCREEN_HEIGHT // 2 + 50))

    def get_overlay_surface(self, frame):
        """Creates a surface with hand landmarks from the camera frame."""
        overlay_frame = np.zeros((frame.shape[0], frame.shape[1], 3), dtype=np.uint8)
        self.tracker.draw_landmarks_on_frame(overlay_frame)
        overlay_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
        overlay_surf = pygame.surfarray.make_surface(overlay_frame.swapaxes(0, 1))
        overlay_surf = pygame.transform.scale(overlay_surf, (320, 180))
        return overlay_surf
