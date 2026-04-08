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
