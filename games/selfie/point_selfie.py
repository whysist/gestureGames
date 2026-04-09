"""
games/selfie/point_selfie.py — Point Selfie mode.
"""

import pygame
import cv2
import numpy as np
from typing import List, Optional, Tuple, Any, Dict

from games.base_game import BaseGame
from gesture.face_tracker import FaceTracker
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE

class PointSelfieGame(BaseGame):
    def __init__(self, screen, clock, tracker):
        # We also need a FaceTracker
        super().__init__(screen, clock, tracker)
        self.face_tracker = FaceTracker()
        self.reset()
        self.font = pygame.font.SysFont("Outfit", 36, bold=True)

    def reset(self):
        self._score = 0
        self._is_over = False
        self.exit_requested = False
        self.faces = []
        self.btn_rect = pygame.Rect(SCREEN_WIDTH // 2 - 60, SCREEN_HEIGHT - 100, 120, 60)

    def update(self, hand_data: Optional[List[Dict[str, Any]]]) -> None:
        # Note: Point Selfie doesn't use hand_data, it needs the full frame.
        # However, the current Architecture passes landmarks.
        # We will handle the face detection in a special way or 
        # modify the main loop to pass the frame if needed.
        # Actually, PointSelfie can just use the shared video capture if we pass it,
        # but the tracker is usually what handles the frame.
        pass

    def update_with_frame(self, frame: np.ndarray):
        """Special update method that takes the raw frame."""
        # Frame is already mirrored and BGR
        self.faces = self.face_tracker.get_face_landmarks(frame)

    def draw(self, screen: pygame.Surface):
        # Point Selfie doesn't use the standard draw because it's split screen
        # We will handle this in main.py for efficiency, or just do it here.
        pass

    def draw_split(self, screen: pygame.Surface, frame: np.ndarray):
        """Draws the split screen view with skull-like connections."""
        half_w = SCREEN_WIDTH // 2
        
        # 1. Left side: Camera feed
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        left_surf = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
        left_surf = pygame.transform.scale(left_surf, (half_w, SCREEN_HEIGHT))
        screen.blit(left_surf, (0, 0))
        
        # 2. Right side: Points and Connections
        right_rect = pygame.Rect(half_w, 0, half_w, SCREEN_HEIGHT)
        pygame.draw.rect(screen, (5, 5, 15), right_rect)
        
        # Access connections from FaceTracker's mediapipe module
        connections = self.face_tracker._mp_face_mesh.FACEMESH_TESSELATION
        
        for face_lms in self.faces:
            # Draw Connections (Skull effect)
            for connection in connections:
                start_idx = connection[0]
                end_idx = connection[1]
                
                start_lm = face_lms[start_idx]
                end_lm = face_lms[end_idx]
                
                pts = [
                    (half_w + int(start_lm[0] * half_w), int(start_lm[1] * SCREEN_HEIGHT)),
                    (half_w + int(end_lm[0] * half_w), int(end_lm[1] * SCREEN_HEIGHT))
                ]
                pygame.draw.line(screen, (100, 100, 200), pts[0], pts[1], 1)

            # Draw Points
            for lm in face_lms:
                px = half_w + int(lm[0] * half_w)
                py = int(lm[1] * SCREEN_HEIGHT)
                if half_w <= px < SCREEN_WIDTH and 0 <= py < SCREEN_HEIGHT:
                    pygame.draw.circle(screen, WHITE, (px, py), 1)

        # 3. UI
        pygame.draw.line(screen, WHITE, (half_w, 0), (half_w, SCREEN_HEIGHT), 2)
        
        # Capture Button
        self.btn_rect = pygame.Rect(half_w - 60, SCREEN_HEIGHT - 100, 120, 60)
        pygame.draw.rect(screen, (0, 240, 255), self.btn_rect, border_radius=15, width=2)
        cap_text = self.font.render("PHOTO", True, (0, 240, 255))
        screen.blit(cap_text, (self.btn_rect.centerx - cap_text.get_width() // 2, 
                               self.btn_rect.centery - cap_text.get_height() // 2))

        # Legend
        camera_text = self.font.render("Live Feed", True, WHITE)
        points_text = self.font.render("Skull Map", True, WHITE)
        screen.blit(camera_text, (20, SCREEN_HEIGHT - 60))
        screen.blit(points_text, (half_w + 20, SCREEN_HEIGHT - 60))

    def take_selfie(self, screen: pygame.Surface):
        """Save only the landmark detection half of the screen."""
        import os
        import time
        if not os.path.exists("captures"):
            os.makedirs("captures")
        
        # Crop to the right half
        half_w = (SCREEN_WIDTH // 2) + 60
        right_side = screen.subsurface((half_w, 0, half_w, SCREEN_HEIGHT))
        
        filename = f"captures/selfie_{int(time.time())}.png"
        pygame.image.save(right_side, filename)
        
        # Flash effect
        flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        flash.fill(WHITE)
        screen.blit(flash, (0,0))
        pygame.display.flip()
        pygame.time.delay(50)
        print(f"Selfie saved to {filename}")

    def cleanup(self):
        self.face_tracker.release()

    def get_overlay_surface(self, frame: np.ndarray) -> pygame.Surface:
        """Required by main.py overlay logic. Returns a small scaled frame."""
        # For Point Selfie, the overlay is somewhat redundant, but we provide it for compatibility.
        small_frame = cv2.resize(frame, (320, 180))
        small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        overlay_surf = pygame.surfarray.make_surface(small_frame.swapaxes(0, 1))
        return overlay_surf
