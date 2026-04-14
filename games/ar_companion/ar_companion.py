"""
games/ar_companion/ar_companion.py — AR Companion mode for Virtual Filters.
"""

import pygame
import cv2
import numpy as np
import os
import time
from typing import List, Optional, Tuple, Any, Dict

from games.base_game import BaseGame
from gesture.face_tracker import FaceTracker
from games.ar_companion.filter_engine import ARFilterEngine
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE, HUB_BG, HUB_ACCENT, HUB_READY_COLOR, GRAY
from ui.text_input import TextInput
from ui.email_utils import send_email_with_photos

class ARCompanionGame(BaseGame):
    def __init__(self, screen, clock, tracker):
        super().__init__(screen, clock, tracker)
        self.font = pygame.font.SysFont("Outfit", 30, bold=True)
        self.face_tracker = FaceTracker()
        self.filter_engine = ARFilterEngine()
        self.reset()

    def reset(self):
        self._score = 0
        self._is_over = False
        self.exit_requested = False
        
        # Photo/Email flow state
        self.show_email_prompt = False
        self.email_input = TextInput(SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 30, 400, 60, self.font, "Enter your email...")
        self.session_photos = [] 
        
        # UI Layout
        self.sidebar_w = 220
        self.cam_rect = pygame.Rect(0, 0, SCREEN_WIDTH - self.sidebar_w, SCREEN_HEIGHT)
        
        # Buttons
        self.btn_rect = pygame.Rect(self.cam_rect.centerx - 130, SCREEN_HEIGHT - 90, 120, 50)
        self.done_btn_rect = pygame.Rect(self.cam_rect.centerx + 10, SCREEN_HEIGHT - 90, 120, 50)
        
        # Filter Menu (Updated with user-downloaded assets)
        self.filters = [
            {"id": "none", "name": "Natural", "file": None},
            {"id": "ironman", "name": "Iron Man", "file": "hero_ironman.png"},
            {"id": "batman", "name": "Batman", "file": "hero_batman.png"},
            {"id": "spiderman", "name": "Spider-Man", "file": "hero_spiderman.png"},
            {"id": "superman", "name": "Superman", "file": "hero_superman.png"},
            {"id": "hulk", "name": "Hulk", "file": "hero_hulk.png"},
            {"id": "dog", "name": "Dog", "file": "animal_dog.png"},
            {"id": "bunny", "name": "Bunny", "file": "animal_cute_bunny.png"},
            {"id": "rabbit", "name": "Rabbit", "file": "animal_rabbit.png"},
            {"id": "chihuahua", "name": "Chihauha", "file": "animal_chihauha_stylish.png"},
            {"id": "beard", "name": "The Beard", "file": "beard.png"},
            {"id": "wings", "name": "Angel Wings", "file": "angel_wings.png"},
            {"id": "aging", "name": "Aging", "file": "texture"},
            {"id": "squish", "name": "Squished", "file": "warp"},
            {"id": "fisheye", "name": "Fisheye", "file": "warp"},
        ]
        self.active_filter_idx = 0
        self.scroll_y = 0
        self.max_scroll = -(len(self.filters) * 70 - (SCREEN_HEIGHT - 100))
        
        self.sending_status = "" 
        self.status_timer = 0
        self.last_landmarks = None

    def update(self, hand_data: Optional[List[Dict[str, Any]]]) -> None:
        pass

    def draw(self, screen: pygame.Surface):
        """Standard draw requirement (AR Companion uses draw_full_ar instead)."""
        pass

    def update_with_frame(self, frame: np.ndarray):
        """Standard update, performs face tracking."""
        if self.status_timer > 0:
            self.status_timer -= 1
            if self.status_timer == 0:
                self.sending_status = ""
        
        # Track face mesh
        faces = self.face_tracker.get_face_landmarks(frame)
        if faces:
            self.last_landmarks = faces[0]
        else:
            self.last_landmarks = None

    def handle_event(self, event):
        if self.show_email_prompt:
            result = self.email_input.handle_event(event)
            if result is not None:
                self.process_email(result)
            return

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if mx > SCREEN_WIDTH - self.sidebar_w:
                if event.button == 4: # Scroll Up
                    self.scroll_y = min(0, self.scroll_y + 30)
                elif event.button == 5: # Scroll Down
                    self.scroll_y = max(self.max_scroll, self.scroll_y - 30)
                elif event.button == 1: # Left Click
                    # Vertical menu click detection
                    item_h = 70
                    start_y = 80 + self.scroll_y
                    for i in range(len(self.filters)):
                        rect = pygame.Rect(SCREEN_WIDTH - self.sidebar_w + 10, start_y + i * item_h, self.sidebar_w - 20, 60)
                        if rect.collidepoint(mx, my):
                            self.active_filter_idx = i
                            break

    def draw_full_ar(self, screen: pygame.Surface, frame: np.ndarray):
        """Draws the full screen AR view with sidebar."""
        # 1. Apply Warp Filters if active (modifies frame)
        active_f = self.filters[self.active_filter_idx]
        if active_f["file"] == "warp":
            frame = self.filter_engine.apply_warp_filter(frame, self.last_landmarks, active_f["id"])
            
        # 2. Background: Camera feed (cropped/scaled to fit cam_rect area)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        cam_surf = pygame.surfarray.make_surface(rgb_frame.swapaxes(0, 1))
        # Scale to match the left section
        cam_surf = pygame.transform.scale(cam_surf, (self.cam_rect.width, self.cam_rect.height))
        screen.blit(cam_surf, (0, 0))
        
        # 3. Apply Asset Filters (Overlays)
        if active_f["file"]:
            if active_f["file"] == "texture":
                self.filter_engine.apply_aging_filter(screen, self.last_landmarks, self.cam_rect)
            elif active_f["file"] != "warp":
                # Pass landmarks, asset filename, and the camera rectangle for correct mapping
                self.filter_engine.apply_asset_filter(screen, self.last_landmarks, active_f["file"], active_f["id"], self.cam_rect)
        
        # 4. Watermark (Easter Egg)
        logo = self.filter_engine.load_asset("snapchat_logo.png")
        if logo:
            logo = pygame.transform.scale(logo, (50, 50))
            screen.blit(logo, (self.cam_rect.right - 60, 20))

        # 5. UI Sidebar
        sidebar_rect = pygame.Rect(SCREEN_WIDTH - self.sidebar_w, 0, self.sidebar_w, SCREEN_HEIGHT)
        pygame.draw.rect(screen, HUB_BG, sidebar_rect)
        pygame.draw.line(screen, HUB_ACCENT, (SCREEN_WIDTH - self.sidebar_w, 0), (SCREEN_WIDTH - self.sidebar_w, SCREEN_HEIGHT), 2)
        
        title = self.font.render("CHARACTERS", True, HUB_READY_COLOR)
        screen.blit(title, (SCREEN_WIDTH - self.sidebar_w // 2 - title.get_width() // 2, 25))
        
        # Draw Menu Items
        item_h = 70
        start_y = 80 + self.scroll_y
        for i, f in enumerate(self.filters):
            rect = pygame.Rect(SCREEN_WIDTH - self.sidebar_w + 10, start_y + i * item_h, self.sidebar_w - 20, 60)
            color = HUB_READY_COLOR if i == self.active_filter_idx else (40, 60, 80)
            pygame.draw.rect(screen, color, rect, border_radius=10)
            if i == self.active_filter_idx:
                 pygame.draw.rect(screen, WHITE, rect, width=2, border_radius=10)
            
            name = self.font.render(f["name"], True, WHITE)
            screen.blit(name, (rect.centerx - name.get_width() // 2, rect.centery - name.get_height() // 2))

        # 5. Main Game Controls
        # Photo Counter
        count_text = self.font.render(f"Batch: {len(self.session_photos)}", True, WHITE)
        screen.blit(count_text, (20, 20))

        # Capture Button
        pygame.draw.rect(screen, HUB_ACCENT, self.btn_rect, border_radius=15)
        cap_text = self.font.render("PHOTO", True, BLACK)
        screen.blit(cap_text, (self.btn_rect.centerx - cap_text.get_width() // 2, 
                               self.btn_rect.centery - cap_text.get_height() // 2))

        # Done/Send Button
        pygame.draw.rect(screen, HUB_READY_COLOR, self.done_btn_rect, border_radius=15)
        done_text = self.font.render("DONE", True, WHITE)
        screen.blit(done_text, (self.done_btn_rect.centerx - done_text.get_width() // 2, 
                                 self.done_btn_rect.centery - done_text.get_height() // 2))

        # Legend / Shortcuts
        help_font = pygame.font.SysFont("Outfit", 20, bold=False)
        help_text = help_font.render("[C] Switch Camera  |  [ESC] Exit to Menu", True, WHITE)
        screen.blit(help_text, (SCREEN_WIDTH // 2 - help_text.get_width() // 2, SCREEN_HEIGHT - 35))

        # Email Prompt Overlay
        if self.show_email_prompt:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            
            prompt_text = self.font.render("Where should we send your AR photos?", True, WHITE)
            screen.blit(prompt_text, (SCREEN_WIDTH // 2 - prompt_text.get_width() // 2, SCREEN_HEIGHT // 2 - 100))
            
            self.email_input.draw(screen)
            
            instruction = help_font.render("Press ENTER to send or ESC to cancel", True, (200, 200, 200))
            screen.blit(instruction, (SCREEN_WIDTH // 2 - instruction.get_width() // 2, SCREEN_HEIGHT // 2 + 60))

        # Status Message
        if self.sending_status:
            status_surf = self.font.render(self.sending_status, True, HUB_ACCENT)
            pygame.draw.rect(screen, HUB_BG, (SCREEN_WIDTH // 2 - 100, 20, 200, 50), border_radius=10)
            screen.blit(status_surf, (SCREEN_WIDTH // 2 - status_surf.get_width() // 2, 25))

    def take_selfie(self, screen: pygame.Surface):
        """Save the full screen."""
        if not os.path.exists("captures"):
            os.makedirs("captures")
        
        # Capture the current screen state (the camera feed)
        full_shot = screen.copy()
        
        photo_path = f"captures/ar_{int(time.time())}_{len(self.session_photos)}.png"
        pygame.image.save(full_shot, photo_path)
        self.session_photos.append(photo_path)
        
        # Flash effect
        flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        flash.fill(WHITE)
        screen.blit(flash, (0,0))
        pygame.display.flip()
        pygame.time.delay(50)
        
        print(f"AR Photo captured locally at {photo_path}")

    def finish_session(self):
        """Trigger the email prompt for the current session batch."""
        if not self.session_photos:
            return
        self.show_email_prompt = True
        self.email_input.reset()

    def process_email(self, email_address):
        self.show_email_prompt = False
        self.sending_status = "Sending..."
        
        success = send_email_with_photos(email_address, self.session_photos)
        
        if success:
            self.sending_status = "Sent!"
            for path in self.session_photos:
                if os.path.exists(path):
                    os.remove(path)
            self.session_photos = [] 
        else:
            self.sending_status = "Error!"
            
        self.status_timer = 120 

    def cleanup(self):
        if self.face_tracker:
            self.face_tracker.release()

    def get_overlay_surface(self, frame: np.ndarray) -> pygame.Surface:
        return pygame.Surface((0,0)) # Not used as AR is full screen
