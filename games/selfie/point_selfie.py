"""
games/selfie/point_selfie.py — Point Selfie mode.
Supports skull mesh visualization, batch photo capture, and email sharing.
"""

import pygame
import cv2
import numpy as np
import os
import time
from typing import List, Optional, Tuple, Any, Dict

from games.base_game import BaseGame
from gesture.face_tracker import FaceTracker
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, GRAY
from ui.text_input import TextInput
from ui.email_utils import send_email_with_photos

class PointSelfieGame(BaseGame):
    def __init__(self, screen, clock, tracker):
        super().__init__(screen, clock, tracker)
        self.face_tracker = FaceTracker()
        self.font = pygame.font.SysFont("Outfit", 24, bold=True)
        self.title_font = pygame.font.SysFont("Outfit", 36, bold=True)
        self.reset()

    def reset(self):
        self._score = 0
        self._is_over = False
        self.exit_requested = False
        self.faces = []
        
        # Email / Batch logic (As requested: "The photos should not be sent one by one but as batches")
        self.show_email_prompt = False
        self.email_input = TextInput(
            SCREEN_WIDTH//2 - 200, SCREEN_HEIGHT//2 - 30,
            400, 60, self.font, "Enter your email...",
        )
        self.session_photos: List[str] = []
        self.sending_status = ""
        self.status_timer = 0
        self.flash_alpha = 0

        self.half_w = SCREEN_WIDTH // 2
        # UI Rects
        # PHOTO button in the center built-in area of the LEFT feed
        self.btn_rect = pygame.Rect(self.half_w // 2 - 60, SCREEN_HEIGHT - 100, 120, 60)
        # DONE button appearing once at least one photo is taken
        self.done_btn_rect = pygame.Rect(SCREEN_WIDTH - 140, SCREEN_HEIGHT - 125, 120, 50)

    def update(self, hand_data: Optional[List[Dict[str, Any]]]) -> None:
        pass

    def update_with_frame(self, frame: np.ndarray):
        """Special update method that takes the raw frame."""
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 25)
        
        if self.status_timer > 0:
            self.status_timer -= 1
            if self.status_timer == 0:
                self.sending_status = ""
                
        self.faces = self.face_tracker.get_face_landmarks(frame)

    def draw(self, screen: pygame.Surface):
        # Point Selfie uses draw_split (called from main.py)
        pass

    def draw_split(self, screen: pygame.Surface, frame: np.ndarray):
        """Draws the split screen view with skull-like connections."""
        half_w = self.half_w
        
        # 1. Left side: Camera feed
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        left_surf = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
        left_surf = pygame.transform.scale(left_surf, (half_w, SCREEN_HEIGHT))
        screen.blit(left_surf, (0, 0))
        
        # 2. Right side: Points and Connections (Skull Map)
        right_rect = pygame.Rect(half_w, 0, half_w, SCREEN_HEIGHT)
        pygame.draw.rect(screen, (5, 5, 15), right_rect)
        
        # Access connections from FaceTracker's mediapipe module
        connections = self.face_tracker._mp_face_mesh.FACEMESH_TESSELATION
        
        for face_lms in self.faces:
            # Draw Connections (Skull effect)
            for connection in connections:
                start_idx = connection[0]
                end_idx = connection[1]
                
                # face_lms is a list of (x, y, z)
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

        # 3. UI Chrome
        pygame.draw.line(screen, WHITE, (half_w, 0), (half_w, SCREEN_HEIGHT), 2)
        
        # PHOTO Button
        pygame.draw.rect(screen, (0, 240, 255), self.btn_rect, border_radius=15, width=2)
        cap_text = self.title_font.render("PHOTO", True, (0, 240, 255))
        screen.blit(cap_text, (self.btn_rect.centerx - cap_text.get_width() // 2, 
                               self.btn_rect.centery - cap_text.get_height() // 2))

        # DONE Button (Prompts email for batch sending)
        if self.session_photos:
            pygame.draw.rect(screen, (0, 255, 150), self.done_btn_rect, border_radius=25)
            dt = self.font.render("DONE", True, BLACK)
            screen.blit(dt, (self.done_btn_rect.centerx - dt.get_width()//2,
                              self.done_btn_rect.centery - dt.get_height()//2))

            # Photo count badge (showing the batch size)
            badge_rect = pygame.Rect(SCREEN_WIDTH - 60, 20, 40, 40)
            pygame.draw.circle(screen, (0, 255, 150), (badge_rect.centerx, badge_rect.centery), 20)
            ct = self.font.render(str(len(self.session_photos)), True, BLACK)
            screen.blit(ct, (badge_rect.centerx - ct.get_width()//2,
                              badge_rect.centery - ct.get_height()//2))

        # Legend
        camera_text = self.font.render("Live Feed", True, WHITE)
        points_text = self.font.render("Skull Map", True, WHITE)
        screen.blit(camera_text, (20, SCREEN_HEIGHT - 60))
        screen.blit(points_text, (half_w + 30, SCREEN_HEIGHT - 60))

        # Flash effect upon capture
        if self.flash_alpha > 0:
            fl = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fl.fill(WHITE)
            fl.set_alpha(self.flash_alpha)
            screen.blit(fl, (0, 0))

        # Email prompt overlay
        if self.show_email_prompt:
            ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 210))
            screen.blit(ov, (0, 0))
            pt = self.title_font.render("Batch Email Sharing", True, (0, 240, 255))
            screen.blit(pt, (SCREEN_WIDTH//2 - pt.get_width()//2, SCREEN_HEIGHT//2 - 120))
            self.email_input.draw(screen)
            hf = pygame.font.SysFont("Outfit", 20)
            count = len(self.session_photos)
            it = hf.render(f"Sending {count} photos as batch. Enter email and press ENTER.", True, WHITE)
            screen.blit(it, (SCREEN_WIDTH//2 - it.get_width()//2, SCREEN_HEIGHT//2 + 60))

        # Status toast
        if self.sending_status:
            color = (0, 255, 100) if self.sending_status == "Sent!" else (255, 100, 100)
            if self.sending_status == "Sending...": color = (255, 255, 255)
            
            sb = pygame.Rect(SCREEN_WIDTH//2 - 100, 30, 200, 50)
            pygame.draw.rect(screen, color, sb, border_radius=25)
            ss = self.font.render(self.sending_status, True, BLACK)
            screen.blit(ss, (SCREEN_WIDTH//2 - ss.get_width()//2,
                              30 + 25 - ss.get_height()//2))

    def handle_event(self, event):
        if self.show_email_prompt:
            result = self.email_input.handle_event(event)
            if result is not None:
                self.process_email(result)
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.btn_rect.collidepoint(event.pos):
                # Trigger capture handled in main.py but we can return status
                return "CAPTURE"
            if self.done_btn_rect.collidepoint(event.pos):
                self.finish_session()

    def take_selfie(self, screen: pygame.Surface):
        """Save captured photos as backup (as request: 'captures in point selfie game should be used as backup')."""
        os.makedirs("captures", exist_ok=True)
        
        # Capture the right half (the Skull Map)
        right_side = screen.subsurface((self.half_w, 0, self.half_w, SCREEN_HEIGHT)).copy()
        
        path = f"captures/skull_batch_{int(time.time())}_{len(self.session_photos)}.png"
        pygame.image.save(right_side, path)
        self.session_photos.append(path) # Added to batch
        self.flash_alpha = 255
        print(f"[PointSelfie] Captured → {path} (Added to batch)")

    def finish_session(self):
        if not self.session_photos:
            return
        self.show_email_prompt = True
        self.email_input.reset()

    def process_email(self, email_address: str):
        self.show_email_prompt = False
        self.sending_status    = "Sending..."
        # Actual batch sending
        success = send_email_with_photos(email_address, self.session_photos)
        if success:
            self.sending_status = "Sent!"
            self.session_photos = [] # Clear batch after success
        else:
            self.sending_status = "Error!"
        self.status_timer = 120

    def cleanup(self):
        if self.face_tracker:
            self.face_tracker.release()

    def get_overlay_surface(self, frame: np.ndarray) -> pygame.Surface:
        return pygame.Surface((0, 0))
