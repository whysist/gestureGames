"""
games/ar_companion/filter_engine.py — Professional AR Engine with Perspective Warping.
"""

import cv2
import pygame
import numpy as np
import os
from typing import List, Tuple, Dict, Any, Optional

class ARFilterEngine:
    def __init__(self):
        self.filters_dir = os.path.join("assets", "filters")
        self.assets: Dict[str, pygame.Surface] = {}
        self.assets_np: Dict[str, np.ndarray] = {}
        
        # Landmark indices for mapping 
        self.ANCHORS = {
            "forehead": 10,
            "chin": 152,
            "nose_bridge": 6,
            "nose_tip": 1,
            "left_temple": 127,
            "right_temple": 356,
            "left_eye_outer": 33,
            "right_eye_outer": 263,
            "left_cheek": 234,
            "right_cheek": 454,
            "mouth_left": 61,
            "mouth_right": 291
        }

    def load_asset(self, filename: str) -> Optional[pygame.Surface]:
        if filename in self.assets:
            return self.assets[filename]
        
        path = os.path.join(self.filters_dir, filename)
        if not os.path.exists(path):
            return None
        
        try:
            surf = pygame.image.load(path).convert_alpha()
            self.assets[filename] = surf
            
            # Pre-cache Numpy RGBA version for warping speed
            aw, ah = surf.get_size()
            rgba = pygame.surfarray.array3d(surf)
            alpha = pygame.surfarray.array_alpha(surf)
            np_asset = np.zeros((ah, aw, 4), dtype=np.uint8)
            np_asset[:,:,:3] = rgba.transpose(1, 0, 2)
            np_asset[:,:,3] = alpha.transpose(1, 0)
            self.assets_np[filename] = np_asset
            
            return surf
        except:
            return None

    def _get_target_quad(self, landmarks: List[Tuple[float, float, float]], target_rect: pygame.Rect, filter_id: str) -> np.ndarray:
        """Calculates 4 points on the face to define the perspective plane."""
        def gp(idx):
            lm = landmarks[idx]
            return [target_rect.x + lm[0] * target_rect.width, 
                    target_rect.y + lm[1] * target_rect.height]

        # Standard face plane corners: Temples, Chin, Forehead
        l_t = gp(self.ANCHORS["left_temple"])
        r_t = gp(self.ANCHORS["right_temple"])
        chin = gp(self.ANCHORS["chin"])
        fore = gp(self.ANCHORS["forehead"])
        
        # Create a bounding quad based on filter type
        if "hero" in filter_id or "ironman" in filter_id or "batman" in filter_id:
            # Full face mask logic
            # Use temple-to-temple for width, forehead-to-chin for height
            # But masks usually sit a bit wider
            width_expand = 1.1
            points = np.float32([
                [l_t[0] - (r_t[0]-l_t[0])*0.1, fore[1]], # Top Left
                [r_t[0] + (r_t[0]-l_t[0])*0.1, fore[1]], # Top Right
                [r_t[0] + (r_t[0]-l_t[0])*0.1, chin[1]], # Bottom Right
                [l_t[0] - (r_t[0]-l_t[0])*0.1, chin[1]]  # Bottom Left
            ])
            return points
        elif "beard" in filter_id:
            # Nose to Chin logic
            nose = gp(self.ANCHORS["nose_bridge"])
            l_cheek = gp(self.ANCHORS["left_cheek"])
            r_cheek = gp(self.ANCHORS["right_cheek"])
            points = np.float32([
                [l_cheek[0], nose[1]], # Top Left
                [r_cheek[0], nose[1]], # Top Right
                [r_cheek[0], chin[1]], # Bottom Right
                [l_cheek[0], chin[1]]  # Bottom Left
            ])
            return points
        
        # Default: Eye region
        eye_l = gp(self.ANCHORS["left_eye_outer"])
        eye_r = gp(self.ANCHORS["right_eye_outer"])
        points = np.float32([
            [eye_l[0] - 20, fore[1]],
            [eye_r[0] + 20, fore[1]],
            [eye_r[0] + 20, nose[1] if "nose" in locals() else eye_r[1] + 50],
            [eye_l[0] - 20, nose[1] if "nose" in locals() else eye_l[1] + 50]
        ])
        return points

    def apply_asset_filter(self, screen: pygame.Surface, landmarks: List[Tuple[float, float, float]], asset_name: str, filter_id: str, target_rect: pygame.Rect):
        """Warps the 2D PNG onto the face using perspective homography."""
        asset_surf = self.load_asset(asset_name)
        if not asset_surf or not landmarks:
            return
        
        asset_np = self.assets_np[asset_name]
        ah, aw = asset_np.shape[:2]

        # 1. Source points (Corners of the original PNG)
        src_pts = np.float32([[0, 0], [aw, 0], [aw, ah], [0, ah]])

        # 2. Destination points (4 points on the face defining the perspective plane)
        dst_pts = self._get_target_quad(landmarks, target_rect, filter_id)

        # 3. Calculate Perspective Transform
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)

        # 4. Warp into the target screen dimensions
        sw, sh = screen.get_size()
        warped_np = cv2.warpPerspective(asset_np, matrix, (sw, sh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))

        # 5. Result back to Pygame (Fast conversion)
        # We check if there's any non-zero alpha locally in the warped region if needed,
        # but just blitting is usually fine in Pygame with a cached surface.
        warped_surf = pygame.image.frombuffer(warped_np.tobytes(), (sw, sh), 'RGBA')
        screen.blit(warped_surf, (0, 0))

    def apply_warp_filter(self, frame: np.ndarray, landmarks: List[Tuple[float, float, float]], mode: str) -> np.ndarray:
        """Enhanced radial warp with adaptive radius."""
        if not landmarks:
            return frame
            
        h, w = frame.shape[:2]
        flex_x, flex_y = np.meshgrid(np.arange(w), np.arange(h))
        flex_x = flex_x.astype(np.float32)
        flex_y = flex_y.astype(np.float32)

        # Calculate face size for adaptive radius
        l_t = landmarks[self.ANCHORS["left_temple"]]
        r_t = landmarks[self.ANCHORS["right_temple"]]
        face_size_px = np.sqrt(((r_t[0]-l_t[0])*w)**2 + ((r_t[1]-l_t[1])*h)**2)
        radius = int(face_size_px * 1.5)

        nose = landmarks[self.ANCHORS["nose_tip"]]
        cx, cy = int(nose[0] * w), int(nose[1] * h)

        dx = flex_x - cx
        dy = flex_y - cy
        r = np.sqrt(dx**2 + dy**2)
        mask = r < radius

        if mode == "fisheye":
            # Radial Expansion
            flex_x[mask] = cx + dx[mask] * (r[mask]/radius)**0.4
            flex_y[mask] = cy + dy[mask] * (r[mask]/radius)**0.4
        elif mode == "squish":
            # Horizontal Pinch
            flex_x[mask] = cx + dx[mask] * 2.0
            
        return cv2.remap(frame, flex_x, flex_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

    def apply_aging_filter(self, screen: pygame.Surface, landmarks: List[Tuple[float, float, float]], target_rect: pygame.Rect):
        """Applies perspective-aware procedural wrinkles."""
        if not landmarks:
            return
            
        # Draw wrinkles to a temporary surface, then warp it into place
        # Actually, since we draw directly to landmarks, it's already perspective-aware
        # BUT we want 'thickness' and 'arc' to scale.
        
        sw, sh = screen.get_size()
        line_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        
        def gp(idx):
            lm = landmarks[idx]
            return (int(target_rect.x + lm[0] * target_rect.width), 
                    int(target_rect.y + lm[1] * target_rect.height))

        # Use eye height for scaling stroke
        l_eye = landmarks[self.ANCHORS["left_eye_outer"]]
        r_eye = landmarks[self.ANCHORS["right_eye_outer"]]
        face_scale = np.sqrt((r_eye[0]-l_eye[0])**2 + (r_eye[1]-l_eye[1])**2)
        thickness = max(1, int(face_scale * 15))

        # Crow's feet
        for eye_idx in [self.ANCHORS["left_eye_outer"], self.ANCHORS["right_eye_outer"]]:
            pos = gp(eye_idx)
            side = -1 if eye_idx == self.ANCHORS["left_eye_outer"] else 1
            length = int(face_scale * 100)
            pygame.draw.line(line_surf, (80, 80, 80, 100), pos, (pos[0] + side * length, pos[1] - length//2), thickness)
            pygame.draw.line(line_surf, (80, 80, 80, 100), pos, (pos[0] + side * length, pos[1] + length//2), thickness)
            
        # Forehead
        f = gp(self.ANCHORS["forehead"])
        arc_w = int(face_scale * 300)
        pygame.draw.arc(line_surf, (80, 80, 80, 100), (f[0]-arc_w//2, f[1]-20, arc_w, 40), 0.2, 2.9, thickness)
        
        screen.blit(line_surf, (0, 0))