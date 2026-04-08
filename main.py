"""
main.py — Entry point for GestureArcade.
"""

import pygame
import cv2
import time
import sys
from gesture.tracker import HandTracker
from ui.hub import Hub
from games.pong.pong_game import PongGame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS

def main():
    # ── Initialization ────────────────────────────────────────────────────────
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("GestureArcade")
    clock = pygame.time.Clock()
    
    # Camera setup
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        sys.exit()

    # Shared Hand Tracker
    tracker = HandTracker()
    
    # Hub and Games
    hub = Hub(screen)
    pong = PongGame(screen, clock, tracker)
    
    current_state = "HUB"
    active_game = None
    
    running = True
    while running:
        # 1. Capture and Process frame
        ret, frame = cap.read()
        if not ret:
            break
        
        # Mirror mode
        frame = cv2.flip(frame, 1)
        
        # Landmark detection
        landmarks = tracker.get_landmarks(frame)
        
        # 2. Event Handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if current_state == "HUB":
                selection = hub.get_game_selection(event)
                if selection == "pong":
                    pong.reset()
                    active_game = pong
                    current_state = "GAME"
            
            elif current_state == "GAME":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    current_state = "HUB"
                    active_game = None

        # 3. Update logic
        if current_state == "GAME" and active_game:
            active_game.update(landmarks)
            if active_game.is_over:
                # Wait 3 seconds then return to hub handled in draw/loop flow
                pass

        # 4. Rendering
        if current_state == "HUB":
            hub.draw()
        elif current_state == "GAME" and active_game:
            active_game.draw(screen)
            
            # Show gesture overlay (PiP)
            overlay = active_game.get_overlay_surface(frame)
            screen.blit(overlay, (SCREEN_WIDTH - 340, 20))
            
            if active_game.is_over:
                pygame.display.flip()
                time.sleep(3)
                current_state = "HUB"
                active_game = None
                continue # Skip the flip at the end

        pygame.display.flip()
        
        # Target 90 FPS; drop frames gracefully if MediaPipe is slow
        # We cap at 90 but the loop might be slower due to MediaPipe
        clock.tick(90)

    # ── Cleanup ───────────────────────────────────────────────────────────────
    cap.release()
    tracker.release()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
