"""
games/base_game.py — Abstract base class for all GestureArcade mini-games.

Every mini-game must:
  - Inherit from BaseGame
  - Implement update(), draw(), and reset()
  - Expose the is_over and score properties

# TODO: add sound effects — import pygame.mixer here and expose a play_sound() hook
"""

from __future__ import annotations

import abc
from typing import List, Optional, Tuple, Any, Dict

import pygame

from gesture.tracker import HandTracker


class BaseGame(abc.ABC):
    """
    Abstract base class shared by all GestureArcade mini-games.

    Parameters
    ----------
    screen  : pygame.Surface  — the main display surface
    clock   : pygame.time.Clock
    tracker : HandTracker     — the shared MediaPipe instance
    """

    def __init__(
        self,
        screen: pygame.Surface,
        clock: pygame.time.Clock,
        tracker: HandTracker,
    ) -> None:
        self.screen = screen
        self.clock = clock
        self.tracker = tracker
        self._score: int = 0
        self._is_over: bool = False
        self.exit_requested = False
        self.ui_font = pygame.font.SysFont("Arial", 24, bold=True)
        self.exit_button_rect = pygame.Rect(20, 20, 120, 40)
        self.exit_hover_timer = 0 # for gesture exit

    # ── Shared UI logic ──────────────────────────────────────────────────────

    def draw_common_ui(self, screen: pygame.Surface, hand_data: Optional[List[Dict[str, Any]]] = None) -> None:
        """Draws the universal exit button and handles gesture hover detection."""
        # Draw button
        color = (200, 50, 50) if self.exit_hover_timer > 0 else (150, 40, 40)
        pygame.draw.rect(screen, color, self.exit_button_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), self.exit_button_rect, width=2, border_radius=10)
        
        exit_text = self.ui_font.render("EXIT (Esc)", True, (255, 255, 255))
        screen.blit(exit_text, (self.exit_button_rect.centerx - exit_text.get_width() // 2, 
                               self.exit_button_rect.centery - exit_text.get_height() // 2))

        # Progress bar for gesture exit if hovering
        if self.exit_hover_timer > 0:
            progress_w = int((self.exit_hover_timer / 90) * self.exit_button_rect.width)
            pygame.draw.rect(screen, (0, 255, 0), (self.exit_button_rect.x, self.exit_button_rect.bottom + 5, progress_w, 5))

        # Check for palm hover (gesture exit)
        is_hovering = False
        if hand_data:
            for hand in hand_data:
                cx, cy = self.tracker.get_palm_center(hand["landmarks"])
                if self.exit_button_rect.collidepoint(cx, cy):
                    is_hovering = True
                    break
        
        if is_hovering:
            self.exit_hover_timer += 1
            if self.exit_hover_timer >= 90: # 1.5 seconds at 60fps (actually clock might be higher but 90 frames is a good delay)
                self.exit_requested = True
        else:
            self.exit_hover_timer = 0

    def check_exit_click(self, mouse_pos: Tuple[int, int]) -> bool:
        """Returns True if the mouse clicked the exit button."""
        if self.exit_button_rect.collidepoint(mouse_pos):
            self.exit_requested = True
            return True
        return False

    # ── Abstract interface ────────────────────────────────────────────────────

    @abc.abstractmethod
    def update(
        self,
        hand_data: Optional[List[Dict[str, Any]]],
    ) -> None:
        """
        Advance the game state by one frame.

        Parameters
        ----------
        hand_data : list of dicts returned by HandTracker.get_landmarks(),
                    or None if no hands are visible.
        """

    @abc.abstractmethod
    def draw(self, screen: pygame.Surface) -> None:
        """Render the current game state onto *screen*."""

    @abc.abstractmethod
    def reset(self) -> None:
        """Reset the game to its initial state (new round / replay)."""

    # ── Shared properties ─────────────────────────────────────────────────────

    @property
    def is_over(self) -> bool:
        """True when the game has reached its terminal condition."""
        return self._is_over

    @property
    def score(self) -> int:
        """Current player score."""
        return self._score
