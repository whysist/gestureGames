"""
config.py — Shared constants for GestureArcade.
All modules import from here so values stay in one place.
"""

# ── Display ─────────────────────────────────────────────────────────────────
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
FPS: int = 60        # base target; pong_game targets 90 and drops frames gracefully

# ── MediaPipe ────────────────────────────────────────────────────────────────
HAND_DETECTION_CONFIDENCE: float = 0.7
HAND_TRACKING_CONFIDENCE: float = 0.5
MAX_NUM_HANDS: int = 2
FACE_DETECTION_CONFIDENCE: float = 0.5
MAX_NUM_FACES: int = 4

# ── Colors (R, G, B) ─────────────────────────────────────────────────────────
WHITE        = (255, 255, 255)
BLACK        = (  0,   0,   0)
GRAY         = (120, 120, 120)
DARK_GRAY    = ( 30,  30,  40)
LIGHT_GRAY   = (200, 200, 200)

NEON_CYAN    = (  0, 240, 255)
NEON_MAGENTA = (255,   0, 200)
NEON_GREEN   = (  0, 255, 100)
NEON_YELLOW  = (255, 230,   0)
NEON_ORANGE  = (255, 120,   0)
FRUIT_APPLE  = (255, 30, 60)
FRUIT_ORANGE = (255, 165, 0)
FRUIT_WATERMELON = (50, 205, 50)
FRUIT_BOMB   = (50, 50, 50)

# Hub palette
HUB_BG           = (  8,   8,  18)   # near-black with a hint of blue
HUB_CARD_BG      = ( 18,  22,  42)
HUB_CARD_BORDER  = ( 40,  60, 100)
HUB_TITLE_COLOR  = NEON_CYAN
HUB_READY_COLOR  = NEON_GREEN
HUB_SOON_COLOR   = GRAY
HUB_ACCENT       = NEON_MAGENTA

# Pong palette
PONG_BG          = (  5,   5,  15)
PONG_BALL_COLOR  = NEON_YELLOW
PONG_PLAYER_COLOR= NEON_CYAN
PONG_AI_COLOR    = NEON_MAGENTA
PONG_NET_COLOR   = ( 60,  60,  80)
PONG_SCORE_COLOR = WHITE

# ── Pong game tuning ─────────────────────────────────────────────────────────
PADDLE_WIDTH: int  = 15
PADDLE_HEIGHT: int = 100
BALL_RADIUS: int   = 15
AI_SPEED: int      = 5          # max pixels per frame the AI paddle can move
WINNING_SCORE: int = 7
BALL_INITIAL_SPEED: float = 6.0
BALL_SPEED_INCREASE: float = 1.05   # multiplicative factor per volley
BALL_TIME_SPEED_INCREASE: float = 1.0003  # multiplicative factor per frame

# ── Fruit Ninja tuning ───────────────────────────────────────────────────────
GRAVITY: float = 0.25
FRUIT_MIN_SPEED_Y: float = -12.0
FRUIT_MAX_SPEED_Y: float = -18.0
FRUIT_MIN_SPEED_X: float = -4.0
FRUIT_MAX_SPEED_X: float = 4.0
FRUIT_RADIUS: int = 40
SLASH_MAX_POINTS: int = 15
MIN_SLASH_VELOCITY: float = 15.0  # Pixels per frame to count as a slice

# ── Flappy Bird tuning ───────────────────────────────────────────────────────
FLAPPY_GRAVITY: float = 0.6
FLAPPY_FLAP_POWER: float = -10.0
FLAPPY_PIPE_SPEED: float = 5.0
FLAPPY_INITIAL_GAP: int = 250
FLAPPY_MIN_GAP: int = 160
FLAPPY_GAP_REDUCTION: float = 5.0  # reduction per point
FLAPPY_PIPE_WIDTH: int = 80
FLAPPY_PIPE_SPACING: int = 400     # horizontal distance between pipes
FLAPPY_BIRD_SIZE: int = 40
FLAPPY_FLAP_THRESHOLD: float = 15.0 # pixels to move down to trigger flap

# ── Air Drumming tuning ──────────────────────────────────────────────────────
DRUM_LANE_COUNT: int = 4
DRUM_TILE_SPEED: float = 6.0
DRUM_HIT_THRESHOLD: float = 12.0  # Downward velocity threshold
DRUM_LANE_WIDTH: int = 200
DRUM_TILE_HEIGHT: int = 40
DRUM_HIT_ZONE_Y: int = 600       # Y-coordinate where tiles must be hit

# ── Finger landmark indices (MediaPipe convention) ───────────────────────────
WRIST           = 0
THUMB_TIP       = 4
INDEX_TIP       = 8
MIDDLE_TIP      = 12
RING_TIP        = 16
PINKY_TIP       = 20
