"""
gesture/face_tracker.py — MediaPipe Face Mesh wrapper.
"""

from __future__ import annotations

import cv2
import mediapipe as mp
import numpy as np
from typing import List, Optional, Tuple, Any, Dict

from config import (
    FACE_DETECTION_CONFIDENCE,
    MAX_NUM_FACES,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
)

class FaceTracker:
    """
    Thin wrapper around mediapipe.solutions.face_mesh.
    """

    def __init__(self) -> None:
        self._mp_face_mesh = mp.solutions.face_mesh
        self._face_mesh = self._mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=MAX_NUM_FACES,
            min_detection_confidence=FACE_DETECTION_CONFIDENCE,
            min_tracking_confidence=0.5
        )
        self._mp_draw = mp.solutions.drawing_utils
        self._drawing_spec = self._mp_draw.DrawingSpec(thickness=1, circle_radius=1, color=(255, 255, 255))

    def get_face_landmarks(self, frame: np.ndarray) -> List[List[Tuple[float, float, float]]]:
        """
        Run face mesh detection on *frame* (mirrored BGR).
        Returns a list of faces, each face being a list of 468 landmarks (x, y, z).
        """
        # Downsample for faster processing
        h, w = frame.shape[:2]
        proc_w = 480
        proc_h = int(h * (proc_w / w))
        small_frame = cv2.resize(frame, (proc_w, proc_h))
        
        rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._face_mesh.process(rgb)
        
        all_face_landmarks = []
        if results.multi_face_landmarks:
            for face_lms in results.multi_face_landmarks:
                landmarks = [(lm.x, lm.y, lm.z) for lm in face_lms.landmark]
                all_face_landmarks.append(landmarks)
        
        return all_face_landmarks

    def release(self) -> None:
        """Close the MediaPipe graph and free resources."""
        self._face_mesh.close()
