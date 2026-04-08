"""
gesture/tracker.py — Shared MediaPipe Hands wrapper.

A single HandTracker instance is created at startup and shared across
all mini-games.  Everything runs synchronously in the game loop thread.
"""

from __future__ import annotations

import cv2
import mediapipe as mp
import numpy as np
from typing import List, Optional, Tuple, Any, Dict

from config import (
    HAND_DETECTION_CONFIDENCE,
    HAND_TRACKING_CONFIDENCE,
    MAX_NUM_HANDS,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)


class HandTracker:
    """
    Thin wrapper around mediapipe.solutions.hands.

    Usage::

        tracker = HandTracker()
        while True:
            ret, frame = cap.read()
            frame = cv2.flip(frame, 1)          # mirror mode
            landmarks_list = tracker.get_landmarks(frame)
            if landmarks_list:
                cx, cy = tracker.get_palm_center(landmarks_list[0])
        tracker.release()
    """

    def __init__(self) -> None:
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=MAX_NUM_HANDS,
            min_detection_confidence=HAND_DETECTION_CONFIDENCE,
            min_tracking_confidence=HAND_TRACKING_CONFIDENCE,
        )
        self._mp_draw = mp.solutions.drawing_utils
        self._last_results = None   # cached for overlay drawing

    # ── Core detection ────────────────────────────────────────────────────────

    def get_landmarks(
        self, frame: np.ndarray
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Run hand detection on *frame* (BGR, already flipped to mirror mode).

        Returns a list of hands, each hand being a dict:
          {
            "landmarks": list of 21 (x, y, z) tuples,
            "label": "Left" or "Right"
          }
        Returns None if no hands detected.
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        self._last_results = results

        if not results.multi_hand_landmarks:
            return None

        hand_data: List[Dict[str, Any]] = []
        for i, hand_lms in enumerate(results.multi_hand_landmarks):
            landmarks: List[Tuple[float, float, float]] = [
                (lm.x, lm.y, lm.z) for lm in hand_lms.landmark
            ]
            
            # Extract handedness label
            # MediaPipe results.multi_handedness[i].classification[0].label
            label = results.multi_handedness[i].classification[0].label
            
            hand_data.append({
                "landmarks": landmarks,
                "label": label
            })

        return hand_data

    # ── Coordinate helpers ────────────────────────────────────────────────────

    def get_palm_center(
        self,
        landmarks: List[Tuple[float, float, float]],
        width: int = SCREEN_WIDTH,
        height: int = SCREEN_HEIGHT,
    ) -> Tuple[int, int]:
        """
        Approximate palm center as the average of the wrist and the four
        MCP (knuckle) landmarks: index(5), middle(9), ring(13), pinky(17).

        Returns pixel coordinates (x, y) clamped to [0, width/height].
        """
        palm_indices = [0, 5, 9, 13, 17]   # wrist + four MCPs
        xs = [landmarks[i][0] for i in palm_indices]
        ys = [landmarks[i][1] for i in palm_indices]
        cx = int(sum(xs) / len(xs) * width)
        cy = int(sum(ys) / len(ys) * height)
        cx = max(0, min(width, cx))
        cy = max(0, min(height, cy))
        return cx, cy

    def get_fingertip(
        self,
        landmarks: List[Tuple[float, float, float]],
        finger_index: int,
        width: int = SCREEN_WIDTH,
        height: int = SCREEN_HEIGHT,
    ) -> Tuple[int, int]:
        """
        Return pixel coordinates of a specific landmark by index.

        Tip landmark indices (MediaPipe convention):
          4  → thumb tip
          8  → index tip
          12 → middle tip
          16 → ring tip
          20 → pinky tip
        """
        lm = landmarks[finger_index]
        x = int(lm[0] * width)
        y = int(lm[1] * height)
        x = max(0, min(width, x))
        y = max(0, min(height, y))
        return x, y

    # ── Overlay helper ────────────────────────────────────────────────────────

    def draw_landmarks_on_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Draw MediaPipe skeleton on *frame* in-place and return it.
        Used by pong_game to produce the gesture overlay surface.
        """
        if self._last_results and self._last_results.multi_hand_landmarks:
            for hand_lms in self._last_results.multi_hand_landmarks:
                self._mp_draw.draw_landmarks(
                    frame,
                    hand_lms,
                    self._mp_hands.HAND_CONNECTIONS,
                    self._mp_draw.DrawingSpec(
                        color=(0, 255, 255), thickness=2, circle_radius=3
                    ),
                    self._mp_draw.DrawingSpec(
                        color=(255, 0, 200), thickness=2
                    ),
                )
        return frame

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def release(self) -> None:
        """Close the MediaPipe graph and free resources."""
        self._hands.close()
