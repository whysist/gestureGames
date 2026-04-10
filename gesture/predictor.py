import time
from typing import List, Tuple, Optional

class HandPredictor:
    """
    Predicts hand landmark positions based on velocity when tracking is lost.
    """
    def __init__(self, max_missed_frames: int = 10):
        self.max_missed_frames = max_missed_frames
        self.missed_frames = 0
        self.last_landmarks: Optional[List[Tuple[float, float, float]]] = None
        self.velocity: Optional[List[Tuple[float, float, float]]] = None
        self.last_t = time.time()

    def update(self, landmarks: Optional[List[Tuple[float, float, float]]]):
        now = time.time()
        dt = now - self.last_t
        self.last_t = now

        if landmarks is not None:
            self.missed_frames = 0
            if self.last_landmarks is not None and dt > 0:
                # Calculate velocity: (current - last) / dt
                self.velocity = [
                    ((curr[0] - last[0]) / dt,
                     (curr[1] - last[1]) / dt,
                     (curr[2] - last[2]) / dt)
                    for curr, last in zip(landmarks, self.last_landmarks)
                ]
            self.last_landmarks = landmarks
            return landmarks
        else:
            self.missed_frames += 1
            if self.missed_frames <= self.max_missed_frames and self.last_landmarks is not None and self.velocity is not None:
                # Predict new position: last + velocity * dt
                predicted = [
                    (last[0] + vel[0] * dt,
                     last[1] + vel[1] * dt,
                     last[2] + vel[2] * dt)
                    for last, vel in zip(self.last_landmarks, self.velocity)
                ]
                # Clamp results to [0, 1] for normalization
                predicted = [
                    (max(0.0, min(1.0, p[0])),
                     max(0.0, min(1.0, p[1])),
                     p[2]) 
                    for p in predicted
                ]
                self.last_landmarks = predicted
                return predicted
            else:
                self.last_landmarks = None
                self.velocity = None
                return None

    def reset(self):
        self.missed_frames = 0
        self.last_landmarks = None
        self.velocity = None
        self.last_t = time.time()
