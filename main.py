"""
main.py — Entry point for GestureArcade.
"""

import pygame
import cv2
import time
import sys
import subprocess
import os
from gesture.tracker import HandTracker
from ui.hub import Hub
from games.pong.pong_game import PongGame
from games.ninja.fruit_ninja import FruitNinjaGame
from games.flappy.flappy_game import FlappyGame
from games.selfie.point_selfie import PointSelfieGame
from games.drum.drum_game import DrumGame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS

# Path to the standalone subway-surfer script
_SURFER_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "games", "subway-surfer", "run.py"
)

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
    ninja = FruitNinjaGame(screen, clock, tracker)
    flappy = FlappyGame(screen, clock, tracker)
    selfie = PointSelfieGame(screen, clock, tracker)
    drum = DrumGame(screen, clock, tracker)
    
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
            
            # Global Escape Key
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if current_state == "HUB":
                    running = False # Quit app
                else:
                    current_state = "HUB" # Return to hub
                    active_game = None

            if current_state == "HUB":
                selection = hub.get_game_selection(event)
                if selection == "pong":
                    pong.reset()
                    active_game = pong
                    current_state = "GAME"
                elif selection == "ninja":
                    ninja.reset()
                    active_game = ninja
                    current_state = "GAME"
                elif selection == "flappy":
                    flappy.reset()
                    active_game = flappy
                    current_state = "GAME"
                elif selection == "selfie":
                    selfie.reset()
                    active_game = selfie
                    current_state = "GAME"
                elif selection == "drum":
                    drum.reset()
                    active_game = drum
                    current_state = "GAME"
                elif selection == "surfer":
                    # Launch the standalone subway-surfer script as a subprocess.
                    # Release the webcam so run.py can open its own capture.
                    cap.release()
                    proc = subprocess.Popen([sys.executable, _SURFER_SCRIPT])
                    proc.wait()   # block until the user closes run.py (ESC)
                    # Re-open the webcam for the hub
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        print("Warning: Could not reopen webcam after surfer exited.")
                    current_state = "HUB"
                
            elif current_state == "GAME":
                if event.type == pygame.MOUSEBUTTONDOWN and active_game:
                    # Check universal exit button
                    if active_game.check_exit_click(event.pos):
                        current_state = "HUB"
                        active_game = None
                    # Check game-specific buttons (like Selfie Capture)
                    elif isinstance(active_game, PointSelfieGame):
                        if active_game.btn_rect.collidepoint(event.pos):
                            active_game.take_selfie(screen)

        # 3. Update logic
        if current_state == "GAME" and active_game:
            if isinstance(active_game, PointSelfieGame):
                active_game.update_with_frame(frame)
            else:
                active_game.update(landmarks)
                
            if active_game.is_over:
                # Wait 3 seconds then return to hub handled in draw/loop flow
                pass

        # 4. Rendering
        if current_state == "HUB":
            hub.draw()
        elif current_state == "GAME" and active_game:
            if isinstance(active_game, PointSelfieGame):
                active_game.draw_split(screen, frame)
            else:
                active_game.draw(screen)
            
            # Draw common UI (Exit button and gesture exit detection)
            active_game.draw_common_ui(screen, landmarks)
            if active_game.exit_requested:
                current_state = "HUB"
                active_game.reset() # reset flag
                active_game = None
                continue
            
            # Show gesture overlay (PiP) - Skip for Point Selfie as it has its own camera view
            if not isinstance(active_game, PointSelfieGame):
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
    selfie.face_tracker.release()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
