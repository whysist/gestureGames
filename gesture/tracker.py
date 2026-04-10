"""
gesture/tracker.py — Shared MediaPipe Hands wrapper with Temporal Smoothing and Motion Prediction.
"""

from __future__ import annotations

import cv2
import mediapipe as mp
import numpy as np
import time
from typing import List, Optional, Tuple, Any, Dict

from gesture.filters import OneEuroFilter
from gesture.predictor import HandPredictor
from config import (
    HAND_DETECTION_CONFIDENCE,
    HAND_TRACKING_CONFIDENCE,
    MAX_NUM_HANDS,
    HAND_MODEL_COMPLEXITY,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    FILTER_ENABLE,
    FILTER_MIN_CUTOFF,
    FILTER_BETA,
    HAND_PERSISTENCE_THRESHOLD
)

class HandTracker:
    """
    Advanced wrapper around mediapipe.solutions.hands.
    Features:
    - OneEuroFilter temporal smoothing
    - Constant velocity motion prediction
    - Persistent hand ID tracking
    """

    def __init__(self) -> None:
        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=MAX_NUM_HANDS,
            model_complexity=HAND_MODEL_COMPLEXITY,
            min_detection_confidence=HAND_DETECTION_CONFIDENCE,
            min_tracking_confidence=HAND_TRACKING_CONFIDENCE,
        )
        self._mp_draw = mp.solutions.drawing_utils
        self._last_results = None   # cached for overlay drawing
        
        # State for persistence and filtering
        # Dict mapping hand_id -> state dict
        self._hand_states: Dict[int, Dict[str, Any]] = {}
        self._next_hand_id = 0

    def _get_new_hand_state(self, initial_landmarks: List[Tuple[float, float, float]]) -> Dict[str, Any]:
        """Initialize filters and predictor for a new hand."""
        filters = []
        for lm in initial_landmarks:
            # Create x, y, z filters for each landmark
            lm_filters = [
                OneEuroFilter(lm[0], min_cutoff=FILTER_MIN_CUTOFF, beta=FILTER_BETA),
                OneEuroFilter(lm[1], min_cutoff=FILTER_MIN_CUTOFF, beta=FILTER_BETA),
                OneEuroFilter(lm[2], min_cutoff=FILTER_MIN_CUTOFF, beta=FILTER_BETA)
            ]
            filters.append(lm_filters)
            
        predictor = HandPredictor()
        predictor.update(initial_landmarks)
        
        return {
            "filters": filters,
            "predictor": predictor,
            "last_landmarks": initial_landmarks,
            "missed_frames": 0,
            "label": "Unknown"
        }

    def get_landmarks(self, frame: np.ndarray) -> Optional[List[Dict[str, Any]]]:
        """
        Run hand detection and apply smoothing/prediction.
        Returns a list of hand data with persistent IDs.
        """
        h, w = frame.shape[:2]
        proc_w = 640
        proc_h = int(h * (proc_w / w))
        small_frame = cv2.resize(frame, (proc_w, proc_h))
        
        rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        self._last_results = results

        detected_hands = []
        if results.multi_hand_landmarks:
            for i, hand_lms in enumerate(results.multi_hand_landmarks):
                landmarks = [(lm.x, lm.y, lm.z) for lm in hand_lms.landmark]
                label = results.multi_handedness[i].classification[0].label
                detected_hands.append({"landmarks": landmarks, "label": label})

        # ── Persistence & Filtering Logic ─────────────────────────────────────
        final_hand_data = []
        used_detected_indices = set()
        
        # 1. Match detected hands to existing states based on wrist position (landmark 0)
        for hand_id, state in list(self._hand_states.items()):
            best_match_idx = -1
            min_dist = HAND_PERSISTENCE_THRESHOLD
            
            last_wrist = state["last_landmarks"][0]
            
            for i, det in enumerate(detected_hands):
                if i in used_detected_indices: continue
                
                curr_wrist = det["landmarks"][0]
                dist = np.sqrt((curr_wrist[0] - last_wrist[0])**2 + (curr_wrist[1] - last_wrist[1])**2)
                
                if dist < min_dist:
                    min_dist = dist
                    best_match_idx = i
            
            if best_match_idx != -1:
                # Update existing state
                det = detected_hands[best_match_idx]
                used_detected_indices.add(best_match_idx)
                
                # Apply smoothing
                processed_lms = []
                for j, lm in enumerate(det["landmarks"]):
                    if FILTER_ENABLE:
                        smoothed = (
                            state["filters"][j][0](lm[0]),
                            state["filters"][j][1](lm[1]),
                            state["filters"][j][2](lm[2])
                        )
                    else:
                        smoothed = lm
                    processed_lms.append(smoothed)
                
                # Update predictor
                state["predictor"].update(processed_lms)
                state["last_landmarks"] = processed_lms
                state["missed_frames"] = 0
                state["label"] = det["label"]
                
                final_hand_data.append({
                    "id": hand_id,
                    "landmarks": processed_lms,
                    "label": state["label"]
                })
            else:
                # Hand missed this frame, try prediction
                predicted_lms = state["predictor"].update(None)
                state["missed_frames"] += 1
                
                if predicted_lms and state["missed_frames"] <= 5: # Grace period
                    state["last_landmarks"] = predicted_lms
                    final_hand_data.append({
                        "id": hand_id,
                        "landmarks": predicted_lms,
                        "label": state.get("label", "Unknown"),
                        "predicted": True
                    })
                else:
                    # Drop hand state
                    del self._hand_states[hand_id]

        # 2. Initialize states for new detected hands
        for i, det in enumerate(detected_hands):
            if i not in used_detected_indices:
                new_id = self._next_hand_id
                self._next_hand_id += 1
                self._hand_states[new_id] = self._get_new_hand_state(det["landmarks"])
                self._hand_states[new_id]["label"] = det["label"]
                
                final_hand_data.append({
                    "id": new_id,
                    "landmarks": det["landmarks"],
                    "label": det["label"]
                })

        return final_hand_data if final_hand_data else None

    # ── Coordinate helpers ────────────────────────────────────────────────────

    def get_palm_center(
        self,
        landmarks: List[Tuple[float, float, float]],
        width: int = SCREEN_WIDTH,
        height: int = SCREEN_HEIGHT,
    ) -> Tuple[int, int]:
        palm_indices = [0, 5, 9, 13, 17]
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
        lm = landmarks[finger_index]
        x = int(lm[0] * width)
        y = int(lm[1] * height)
        x = max(0, min(width, x))
        y = max(0, min(height, y))
        return x, y

    # ── Overlay helper ────────────────────────────────────────────────────────

    def draw_landmarks_on_frame(self, frame: np.ndarray) -> np.ndarray:
        if self._last_results and self._last_results.multi_hand_landmarks:
            for hand_lms in self._last_results.multi_hand_landmarks:
                self._mp_draw.draw_landmarks(
                    frame,
                    hand_lms,
                    self._mp_hands.HAND_CONNECTIONS,
                    self._mp_draw.DrawingSpec(color=(0, 255, 255), thickness=2, circle_radius=3),
                    self._mp_draw.DrawingSpec(color=(255, 0, 200), thickness=2),
                )
        return frame

    def release(self) -> None:
        self._hands.close()
