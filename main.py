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
from games.ar_companion.ar_companion import ARCompanionGame
from games.breakout.brick_breaker import BreakoutGame
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
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, SCREEN_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SCREEN_HEIGHT)
    
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        sys.exit()

    # Shared Hand Tracker
    tracker = HandTracker()
    
    # Hub and Games
    hub = Hub(screen)
    pong = PongGame(screen, clock, tracker)
    ar_companion = ARCompanionGame(screen, clock, tracker)
    breakout = BreakoutGame(screen, clock, tracker)
    
    current_state = "HUB"
    active_game = None
    camera_index = 0
    
    def cycle_camera(current_index, current_cap):
        next_index = current_index + 1
        print(f"Switching camera to index {next_index}...")
        new_cap = cv2.VideoCapture(next_index)
        
        # Set High Definition resolution for the new camera
        new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, SCREEN_WIDTH)
        new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SCREEN_HEIGHT)
        
        if not new_cap.isOpened():
            print("No more cameras found. Looping back to 0.")
            new_cap.release()
            new_cap = cv2.VideoCapture(0)
            new_cap.set(cv2.CAP_PROP_FRAME_WIDTH, SCREEN_WIDTH)
            new_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SCREEN_HEIGHT)
            return 0, new_cap
        
        current_cap.release()
        return next_index, new_cap

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
            
            # Global Camera Switch Key 'C' check in HUB or GAME
            if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
                camera_index, cap = cycle_camera(camera_index, cap)

            if current_state == "HUB":
                selection = hub.get_game_selection(event)
                if selection == "pong":
                    pong.reset()
                    active_game = pong
                    current_state = "GAME"
                elif selection == "selfie":
                    ar_companion.reset()
                    active_game = ar_companion
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
                elif selection == "breakout":
                    breakout.reset()
                    active_game = breakout
                    current_state = "GAME"
                
            elif current_state == "GAME":
                if active_game and hasattr(active_game, 'handle_event'):
                    active_game.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN and active_game:
                    # Check universal exit button
                    if active_game.check_exit_click(event.pos):
                        current_state = "HUB"
                        active_game = None
                    # Check game-specific buttons (like Selfie Capture)
                    elif isinstance(active_game, ARCompanionGame):
                        if not active_game.show_email_prompt:
                            if active_game.btn_rect.collidepoint(event.pos):
                                active_game.take_selfie(screen)
                            elif active_game.done_btn_rect.collidepoint(event.pos):
                                active_game.finish_session()

        # 3. Update logic
        if current_state == "GAME" and active_game:
            if isinstance(active_game, ARCompanionGame):
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
            if isinstance(active_game, ARCompanionGame):
                active_game.draw_full_ar(screen, frame)
            else:
                active_game.draw(screen)
            
            # Draw common UI (Exit button and gesture exit detection)
            active_game.draw_common_ui(screen, landmarks)
            if active_game.exit_requested:
                current_state = "HUB"
                active_game.reset() # reset flag
                active_game = None
                continue
            
            # Show gesture overlay (PiP) - Skip for AR Companion as it is full screen
            if not isinstance(active_game, ARCompanionGame):
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
    ar_companion.cleanup()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
