"""
games/surfer/subway_surfer.py — Gesture-controlled Subway Surfer game.

Controls:
  - Swipe index finger OR whole hand LEFT  → move left lane
  - Swipe index finger OR whole hand RIGHT → move right lane

Rules:
  - 3 horizontal lanes; player runs straight (camera scrolls toward you).
  - Stationary train/barrier obstacles fall into view.
  - Speed increases over time.
  - No jumps or rolls — left/right only.
"""

from __future__ import annotations

import pygame
import random
import math
import numpy as np
import cv2
from typing import List, Optional, Dict, Any, Tuple
from collections import deque

from games.base_game import BaseGame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, INDEX_TIP, WRIST

# ── Palette ──────────────────────────────────────────────────────────────────
SKY_TOP       = (10,  8, 30)
SKY_BOT       = (30, 15, 60)
TRACK_DARK    = (20, 18, 35)
TRACK_LINE    = (80, 60, 120)
RAIL_COLOR    = (180, 160, 200)
BUILDING_COLS = [(25,20,50),(35,25,65),(20,25,55),(40,20,45)]

PLAYER_BODY   = (255, 210,  60)   # gold
PLAYER_LEGS   = (255, 120,  20)   # orange
PLAYER_TRAIL  = (255, 240, 100)

TRAIN_BODY    = (200,  30,  50)   # red train
TRAIN_WIN     = ( 40, 120, 200)   # blue windows
TRAIN_STRIPE  = (255, 180,   0)   # yellow stripe

NEON_CYAN   = (  0, 240, 255)
NEON_MAG    = (255,   0, 200)
WHITE       = (255, 255, 255)
BLACK       = (  0,   0,   0)

# ── Layout ────────────────────────────────────────────────────────────────────
NUM_LANES     = 3
LANE_WIDTH    = 220
TRACK_LEFT    = (SCREEN_WIDTH - NUM_LANES * LANE_WIDTH) // 2   # 200
LANE_CENTERS  = [TRACK_LEFT + LANE_WIDTH * i + LANE_WIDTH // 2 for i in range(NUM_LANES)]

PLAYER_Y      = int(SCREEN_HEIGHT * 0.76)
PLAYER_W      = 60
PLAYER_H      = 90

TRAIN_W       = 200
TRAIN_H       = 120
SPAWN_Y       = -TRAIN_H - 20

# ── Speed / difficulty ────────────────────────────────────────────────────────
INITIAL_SPEED    = 5.0
SPEED_INCREMENT  = 0.0008   # per frame
MAX_SPEED        = 28.0

# ── Swipe detection ───────────────────────────────────────────────────────────
SWIPE_HISTORY    = 12       # frames of position history
SWIPE_THRESHOLD  = 55       # pixels of net horizontal movement to trigger swipe
SWIPE_COOLDOWN   = 28       # frames before another swipe is detected

# ── Obstacle spawning ─────────────────────────────────────────────────────────
BASE_SPAWN_INTERVAL  = 110  # frames; decreases with speed
MIN_SPAWN_INTERVAL   = 38

# ── Music: procedural synth ───────────────────────────────────────────────────
SAMPLE_RATE    = 44100
BPM            = 145


def _make_wave(freq: float, duration: float, waveform: str = "square",
               vol: float = 0.3, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    if waveform == "square":
        wave = np.sign(np.sin(2 * np.pi * freq * t)) * vol
    elif waveform == "sawtooth":
        wave = (2 * (freq * t % 1) - 1) * vol
    elif waveform == "sine":
        wave = np.sin(2 * np.pi * freq * t) * vol
    else:
        wave = np.sin(2 * np.pi * freq * t) * vol
    return wave.astype(np.float32)


def _note_freq(semitone_offset: int, base_hz: float = 220.0) -> float:
    return base_hz * (2 ** (semitone_offset / 12))


def _build_music_loop(bpm: int = BPM, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Build a 4-bar looping chiptune track inspired by upbeat runner game vibes.
    All notes generated programmatically — no copyrighted samples used.
    """
    beat_dur   = 60.0 / bpm          # seconds per beat
    bar_dur    = beat_dur * 4
    total_dur  = bar_dur * 4         # 4 bars
    total_samp = int(sample_rate * total_dur)
    buf        = np.zeros(total_samp, dtype=np.float32)

    def place(wave_arr: np.ndarray, start_sec: float):
        s = int(start_sec * sample_rate)
        e = min(s + len(wave_arr), total_samp)
        buf[s:e] += wave_arr[:e - s]

    # ── Melody (square wave) — pentatonic riff ────────────────────────────────
    # Semitone offsets from A3=220 Hz  (A pentatonic: 0,3,5,7,10)
    melody_pattern = [
        # bar 1
        (0, 0), (3, 0.5), (5, 1.0), (7, 1.5),
        (10, 2.0), (7, 2.5), (5, 3.0), (3, 3.5),
        # bar 2
        (0, 4), (5, 4.5), (7, 5.0), (10, 5.5),
        (12, 6.0), (10, 6.5), (7, 7.0), (5, 7.5),
        # bar 3 (higher)
        (12, 8), (10, 8.5), (7, 9.0), (5, 9.5),
        (7, 10.0), (10, 10.5), (12, 11.0), (15, 11.5),
        # bar 4 (resolve)
        (12, 12), (10, 12.5), (7, 13.0), (5, 13.5),
        (3, 14.0), (0, 14.5), (3, 15.0), (0, 15.5),
    ]
    for semitone, beat_idx in melody_pattern:
        freq = _note_freq(semitone, base_hz=440.0)
        w = _make_wave(freq, beat_dur * 0.45, waveform="square", vol=0.22)
        place(w, beat_idx * beat_dur)

    # ── Bass (sawtooth) — root + fifth pattern ────────────────────────────────
    bass_pattern = [
        # root (A2=110Hz) on beats 1&3, fifth (E3) on 2&4
        (0, 0), (7, 1), (0, 2), (7, 3),
        (0, 4), (7, 5), (0, 6), (7, 7),
        (5, 8), (12, 9), (5, 10), (12, 11),
        (3, 12), (10, 13), (3, 14), (0, 15),
    ]
    for semitone, beat_idx in bass_pattern:
        freq = _note_freq(semitone, base_hz=110.0)
        w = _make_wave(freq, beat_dur * 0.85, waveform="sawtooth", vol=0.18)
        place(w, beat_idx * beat_dur)

    # ── Hi-hat (high sine bursts) — 8th notes ─────────────────────────────────
    hat_dur = beat_dur * 0.08
    for i in range(int(total_dur / (beat_dur * 0.5))):
        w = _make_wave(8000, hat_dur, waveform="sine", vol=0.06)
        # apply fast decay
        decay = np.linspace(1, 0, len(w)) ** 3
        w = (w * decay).astype(np.float32)
        place(w, i * beat_dur * 0.5)

    # ── Kick (low sine thump) — beats 1 & 3 ──────────────────────────────────
    for beat_idx in range(16):
        if beat_idx % 2 == 0:
            w = _make_wave(60, beat_dur * 0.25, waveform="sine", vol=0.40)
            decay = np.linspace(1, 0, len(w)) ** 2
            w = (w * decay).astype(np.float32)
            place(w, beat_idx * beat_dur)

    # ── Snare (noise burst) — beats 2 & 4 ────────────────────────────────────
    rng = np.random.default_rng(42)
    for beat_idx in range(16):
        if beat_idx % 2 == 1:
            noise = rng.uniform(-1, 1, int(sample_rate * beat_dur * 0.12)).astype(np.float32) * 0.18
            decay = np.linspace(1, 0, len(noise)) ** 2
            noise = (noise * decay).astype(np.float32)
            place(noise, beat_idx * beat_dur)

    # Clamp and convert to int16 stereo
    buf = np.clip(buf, -1, 1)
    stereo = np.column_stack([buf, buf])
    stereo_int16 = (stereo * 32767).astype(np.int16)
    return stereo_int16


# ── Building decoration ───────────────────────────────────────────────────────
class Building:
    def __init__(self, x: int, w: int, h: int, color: Tuple):
        self.x = x
        self.w = w
        self.h = h
        self.color = color
        self.y = SCREEN_HEIGHT - h - 60  # sit on ground

    def draw(self, screen: pygame.Surface, scroll_y: float):
        # Buildings are cityscape BG — they scroll up slightly (parallax)
        py = int(self.y + scroll_y * 0.08)
        rect = pygame.Rect(self.x, py, self.w, self.h)
        pygame.draw.rect(screen, self.color, rect)
        # Windows
        win_size = 12
        for wy in range(py + 10, py + self.h - 10, 24):
            for wx in range(self.x + 8, self.x + self.w - 8, 20):
                lit = random.random() < 0.6
                wcol = (255, 220, 80) if lit else (30, 30, 60)
                pygame.draw.rect(screen, wcol, (wx, wy, win_size, win_size))


# ── Train obstacle ────────────────────────────────────────────────────────────
class TrainObstacle:
    def __init__(self, lane: int, y: float):
        self.lane  = lane
        self.x     = LANE_CENTERS[lane]
        self.y     = y
        self.w     = TRAIN_W
        self.h     = TRAIN_H
        self.alive = True
        # Variation: occasionally block 2 lanes
        self.extra_lane: Optional[int] = None
        if random.random() < 0.25 and NUM_LANES == 3:
            adj = random.choice([-1, 1])
            if 0 <= lane + adj < NUM_LANES:
                self.extra_lane = lane + adj

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(self.x - self.w // 2, int(self.y) - self.h // 2, self.w, self.h)

    def get_occupied_lanes(self) -> List[int]:
        lanes = [self.lane]
        if self.extra_lane is not None:
            lanes.append(self.extra_lane)
        return lanes

    def update(self, speed: float):
        self.y += speed
        if self.y - self.h // 2 > SCREEN_HEIGHT + 50:
            self.alive = False

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return

        # Draw for each occupied lane
        for lx in ([self.x] + ([LANE_CENTERS[self.extra_lane]] if self.extra_lane is not None else [])):
            rx = lx - self.w // 2
            ry = int(self.y) - self.h // 2

            # Body
            pygame.draw.rect(screen, TRAIN_BODY, (rx, ry, self.w, self.h), border_radius=8)
            # Yellow stripe
            pygame.draw.rect(screen, TRAIN_STRIPE, (rx, ry + self.h // 3, self.w, 12))
            # Windows row
            for wi in range(3):
                wx = rx + 18 + wi * 60
                wy = ry + 14
                pygame.draw.rect(screen, TRAIN_WIN, (wx, wy, 40, 30), border_radius=4)
                pygame.draw.rect(screen, (100, 180, 255), (wx, wy, 40, 30), width=2, border_radius=4)
            # Front face detail (bottom of train = approaching face)
            pygame.draw.rect(screen, (240, 50, 60), (rx + 10, ry + self.h - 30, self.w - 20, 25), border_radius=4)
            # Headlights
            pygame.draw.circle(screen, (255, 255, 150), (rx + 28, ry + self.h - 18), 10)
            pygame.draw.circle(screen, (255, 255, 150), (rx + self.w - 28, ry + self.h - 18), 10)
            pygame.draw.circle(screen, (255, 255, 255), (rx + 28, ry + self.h - 18), 5)
            pygame.draw.circle(screen, (255, 255, 255), (rx + self.w - 28, ry + self.h - 18), 5)
            # Glow
            glow_surf = pygame.Surface((self.w + 40, self.h + 40), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (200, 30, 50, 30), (0, 0, self.w + 40, self.h + 40), border_radius=18)
            screen.blit(glow_surf, (rx - 20, ry - 20))

    def check_collision(self, player_lane: int, player_y: int) -> bool:
        if player_lane not in self.get_occupied_lanes():
            return False
        train_ry = int(self.y) - self.h // 2
        train_bot = train_ry + self.h
        player_top = player_y - PLAYER_H // 2
        player_bot = player_y + PLAYER_H // 2
        return train_bot >= player_top and train_ry <= player_bot


# ── Runner (player) ─────────────────────────────────────────────────────────
class Player:
    def __init__(self):
        self.lane       = 1                    # centre lane (0=left,1=mid,2=right)
        self.x          = float(LANE_CENTERS[1])
        self.y          = float(PLAYER_Y)
        self.target_x   = float(LANE_CENTERS[1])
        self.lane_start_x = float(LANE_CENTERS[1])
        self.anim_t     = 0.0                  # 0→1 slide progress
        self.sliding    = False
        self.dead       = False
        self.flash      = 0                    # death flicker counter
        self.trail: deque = deque(maxlen=18)
        self.bob        = 0.0                  # vertical running bob

    def start_slide(self, new_lane: int):
        """Initiate a smooth lane change.  Always sets lane_start_x before anim starts."""
        if self.dead:
            return
        if new_lane == self.lane and not self.sliding:
            return
        self.lane_start_x = self.x             # capture current position as start
        self.lane         = new_lane
        self.target_x     = float(LANE_CENTERS[new_lane])
        self.sliding      = True
        self.anim_t       = 0.0

    def update(self, speed: float):
        if self.dead:
            self.flash = max(0, self.flash - 1)
            return

        # Smooth ease-out lane slide
        if self.sliding:
            self.anim_t = min(1.0, self.anim_t + 0.14)
            t = 1 - (1 - self.anim_t) ** 3    # ease-out cubic
            self.x = self.lane_start_x + t * (self.target_x - self.lane_start_x)
            if self.anim_t >= 1.0:
                self.x       = self.target_x
                self.sliding = False

        # Running bob
        self.bob = math.sin(pygame.time.get_ticks() * 0.012) * 5
        self.trail.append((int(self.x), int(self.y + self.bob)))

    def kill(self):
        self.dead  = True
        self.flash = 45

    def draw(self, screen: pygame.Surface):
        if self.dead and self.flash % 6 < 3:
            return  # death flicker

        cx, cy = int(self.x), int(self.y + self.bob)

        # Trail
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(180 * i / len(self.trail))
            r = max(2, int(10 * i / len(self.trail)))
            s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*PLAYER_TRAIL, alpha), (r, r), r)
            screen.blit(s, (tx - r, ty - r))

        # Body (capsule-like)
        # Legs
        leg_bounce = int(math.sin(pygame.time.get_ticks() * 0.02) * 8)
        leg_w = 14
        pygame.draw.rect(screen, PLAYER_LEGS,
                         (cx - 18, cy + 20, leg_w, 35 - leg_bounce), border_radius=6)
        pygame.draw.rect(screen, PLAYER_LEGS,
                         (cx + 5,  cy + 20, leg_w, 35 + leg_bounce), border_radius=6)

        # Torso
        pygame.draw.rect(screen, PLAYER_BODY,
                         (cx - 22, cy - 30, 44, 52), border_radius=10)

        # Arms swinging
        arm_swing = int(math.sin(pygame.time.get_ticks() * 0.02 + math.pi) * 15)
        pygame.draw.rect(screen, PLAYER_BODY,
                         (cx - 38, cy - 20 + arm_swing, 18, 10), border_radius=5)
        pygame.draw.rect(screen, PLAYER_BODY,
                         (cx + 20, cy - 20 - arm_swing, 18, 10), border_radius=5)

        # Head
        pygame.draw.circle(screen, (255, 200, 140), (cx, cy - 42), 22)
        # Eyes
        pygame.draw.circle(screen, BLACK, (cx - 8, cy - 45), 4)
        pygame.draw.circle(screen, BLACK, (cx + 8, cy - 45), 4)
        pygame.draw.circle(screen, WHITE, (cx - 7, cy - 46), 2)
        pygame.draw.circle(screen, WHITE, (cx + 9, cy - 46), 2)
        # Hair
        pygame.draw.arc(screen, (80, 40, 10),
                        pygame.Rect(cx - 22, cy - 64, 44, 30), 0, math.pi, 4)

        # Neon outline aura
        glow = pygame.Surface((80, 120), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*NEON_CYAN, 18), (0, 0, 80, 120), border_radius=20)
        screen.blit(glow, (cx - 40, cy - 60))


# ── Main Game ─────────────────────────────────────────────────────────────────
class SubwaySurferGame(BaseGame):

    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock, tracker) -> None:
        super().__init__(screen, clock, tracker)
        self.font       = pygame.font.SysFont("Arial", 34, bold=True)
        self.big_font   = pygame.font.SysFont("Arial", 80, bold=True)
        self.small_font = pygame.font.SysFont("Arial", 22, bold=True)

        # Music
        self._music_channel: Optional[pygame.mixer.Channel] = None
        self._music_sound:   Optional[pygame.mixer.Sound]   = None
        self._init_music()

        # Background buildings (generated once)
        self._buildings = self._gen_buildings()

        # Per-hand swipe buffers: hand_id → deque of (x, y, t_frame)
        self._hand_hist: Dict[int, deque] = {}
        self._swipe_cooldown = 0

        self.reset()

    # ── Music ─────────────────────────────────────────────────────────────────

    def _init_music(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=2048)
            loop_data = _build_music_loop()
            sound = pygame.sndarray.make_sound(loop_data)
            self._music_sound = sound
        except Exception as e:
            print(f"[SubwaySurfer] Music init failed: {e}")
            self._music_sound = None

    def _start_music(self):
        if self._music_sound:
            try:
                self._music_channel = self._music_sound.play(loops=-1)
                if self._music_channel:
                    self._music_channel.set_volume(0.55)
            except Exception:
                pass

    def _stop_music(self):
        try:
            if self._music_channel:
                self._music_channel.stop()
        except Exception:
            pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _gen_buildings(self) -> List[Building]:
        buildings = []
        rng = random.Random(0)  # deterministic for consistent look
        x = 0
        while x < SCREEN_WIDTH:
            w = rng.randint(60, 130)
            h = rng.randint(120, 380)
            color = rng.choice(BUILDING_COLS)
            buildings.append(Building(x, w, h, color))
            x += w + rng.randint(0, 20)
        return buildings

    def reset(self) -> None:
        self._score           = 0
        self._is_over         = False
        self.exit_requested   = False
        self._speed           = INITIAL_SPEED
        self._frame           = 0
        self._spawn_timer     = 0
        self._scroll_y        = 0.0
        self._swipe_cooldown  = 0

        self.player    = Player()
        self.obstacles: List[TrainObstacle] = []

        # Swipe detection state
        self._hand_hist.clear()

        # Countdown
        self._state       = "COUNTDOWN"   # COUNTDOWN / PLAYING / DEAD
        self._countdown_t = pygame.time.get_ticks()
        self._dead_t      = 0

        self._start_music()

    # ── Swipe detection ───────────────────────────────────────────────────────

    def _get_control_x(self, landmarks) -> float:
        """
        Returns a screen-space X by averaging index tip and palm center.
        This handles both 'index only' and 'full hand' swipes.
        """
        # Index fingertip (landmark 8)
        tip_x, _ = self.tracker.get_fingertip(landmarks, INDEX_TIP)
        # Wrist (landmark 0)
        wrist = landmarks[WRIST]
        wrist_x = int(wrist[0] * SCREEN_WIDTH)
        # Average — gives a position that responds to either index OR whole palm movement
        return (tip_x + wrist_x) / 2.0

    def _process_swipes(self, hand_data: Optional[List[Dict[str, Any]]]):
        """Update per-hand position history and detect left/right swipes."""
        if self._swipe_cooldown > 0:
            self._swipe_cooldown -= 1
            return

        active_ids = set()
        if hand_data:
            for hand in hand_data:
                hid = hand["id"]
                active_ids.add(hid)
                lm = hand["landmarks"]

                ctrl_x = self._get_control_x(lm)

                if hid not in self._hand_hist:
                    self._hand_hist[hid] = deque(maxlen=SWIPE_HISTORY)
                self._hand_hist[hid].append(ctrl_x)

                history = self._hand_hist[hid]
                if len(history) >= SWIPE_HISTORY:
                    oldest = history[0]
                    newest = history[-1]
                    delta  = newest - oldest

                    # Also compute peak-to-trough for robustness
                    hist_list = list(history)
                    net_motion = newest - oldest

                    if abs(delta) > SWIPE_THRESHOLD:
                        direction = 1 if delta > 0 else -1  # +1 = right, -1 = left
                        new_lane  = self.player.lane + direction
                        if 0 <= new_lane < NUM_LANES:
                            self.player.start_slide(new_lane)
                        else:
                            # Clamp but still acknowledge swipe
                            new_lane = max(0, min(NUM_LANES - 1, new_lane))
                            self.player.start_slide(new_lane)
                        # Reset history to prevent repeat triggers
                        self._hand_hist[hid].clear()
                        self._swipe_cooldown = SWIPE_COOLDOWN
                        break   # one swipe per frame is enough

        # Prune stale hands
        for hid in list(self._hand_hist.keys()):
            if hid not in active_ids:
                del self._hand_hist[hid]

    # ── Lane-safe spawn helper ────────────────────────────────────────────────

    def _spawn_obstacle(self):
        # Avoid spawning a train where the player currently is (give some grace)
        occupied = {self.player.lane}
        free_lanes = [l for l in range(NUM_LANES) if l not in occupied]
        if not free_lanes:
            free_lanes = list(range(NUM_LANES))
        lane = random.choice(free_lanes)
        self.obstacles.append(TrainObstacle(lane, float(SPAWN_Y)))

    # ── BaseGame interface ────────────────────────────────────────────────────

    def update(self, hand_data: Optional[List[Dict[str, Any]]]) -> None:
        if self._is_over:
            return

        # ── Countdown ─────────────────────────────────────────────────────────
        if self._state == "COUNTDOWN":
            elapsed = (pygame.time.get_ticks() - self._countdown_t) / 1000
            if elapsed >= 3:
                self._state = "PLAYING"
            return

        # ── Dead (brief pause before game over) ───────────────────────────────
        if self._state == "DEAD":
            if pygame.time.get_ticks() - self._dead_t > 1800:
                self._is_over = True
                self._stop_music()
            self.player.update(0)
            return

        # ── Playing ───────────────────────────────────────────────────────────
        self._frame += 1

        # Increase speed
        self._speed = min(MAX_SPEED, INITIAL_SPEED + self._frame * SPEED_INCREMENT)

        # Swipe input
        self._process_swipes(hand_data)

        # Player
        self.player.update(self._speed)

        # Scroll
        self._scroll_y += self._speed

        # Obstacle spawning
        self._spawn_timer += 1
        spawn_interval = max(MIN_SPAWN_INTERVAL,
                             int(BASE_SPAWN_INTERVAL - (self._speed - INITIAL_SPEED) * 4.5))
        if self._spawn_timer >= spawn_interval:
            self._spawn_obstacle()
            self._spawn_timer = 0

        # Update obstacles & collision
        for obs in self.obstacles:
            obs.update(self._speed)
            if not self.player.dead and obs.check_collision(self.player.lane, PLAYER_Y):
                self.player.kill()
                self._state  = "DEAD"
                self._dead_t = pygame.time.get_ticks()

        self.obstacles = [o for o in self.obstacles if o.alive]

        # Score = distance survived (frames)
        if self._state == "PLAYING":
            self._score = self._frame // 10

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw(self, screen: pygame.Surface) -> None:
        # Sky gradient
        sky_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        for y in range(SCREEN_HEIGHT):
            t  = y / SCREEN_HEIGHT
            r  = int(SKY_TOP[0] + t * (SKY_BOT[0] - SKY_TOP[0]))
            g  = int(SKY_TOP[1] + t * (SKY_BOT[1] - SKY_TOP[1]))
            b  = int(SKY_TOP[2] + t * (SKY_BOT[2] - SKY_TOP[2]))
            pygame.draw.line(sky_surf, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        screen.blit(sky_surf, (0, 0))

        # Buildings (parallax BG)
        for bld in self._buildings:
            bld.draw(screen, self._scroll_y)

        # Track lanes
        self._draw_track(screen)

        # Obstacles
        for obs in self.obstacles:
            obs.draw(screen)

        # Player
        self.player.draw(screen)

        # HUD
        self._draw_hud(screen)

        # State overlays
        if self._state == "COUNTDOWN":
            self._draw_countdown(screen)
        elif self._state == "DEAD":
            self._draw_crash_overlay(screen)

    def _draw_track(self, screen: pygame.Surface):
        track_x = TRACK_LEFT
        track_w = NUM_LANES * LANE_WIDTH
        track_rect = pygame.Rect(track_x, 0, track_w, SCREEN_HEIGHT)

        # Dark track surface
        track_surf = pygame.Surface((track_w, SCREEN_HEIGHT), pygame.SRCALPHA)
        track_surf.fill((*TRACK_DARK, 220))
        screen.blit(track_surf, (track_x, 0))

        # Perspective rail lines (converging toward top)
        vp_x = SCREEN_WIDTH // 2   # vanishing point X
        vp_y = int(SCREEN_HEIGHT * 0.30)  # vanishing point Y

        scroll_offset = int(self._scroll_y) % 80  # animated scroll

        for lane_idx in range(NUM_LANES + 1):
            bx = track_x + lane_idx * LANE_WIDTH
            # Draw a line from vanishing point to bottom
            pygame.draw.line(screen, TRACK_LINE, (vp_x, vp_y), (bx, SCREEN_HEIGHT), 2)

            # Rail (left side of lane divider)
            pygame.draw.line(screen, RAIL_COLOR, (vp_x, vp_y), (bx, SCREEN_HEIGHT), 1)

        # Horizontal tie marks (scrolling)
        for ht in range(-1, 20):
            t = (ht * 80 + scroll_offset) / (SCREEN_HEIGHT - vp_y)
            if not (0 < t <= 1):
                continue
            y_pos = int(vp_y + t * (SCREEN_HEIGHT - vp_y))
            left_x  = int(vp_x + (track_x - vp_x) * t)
            right_x = int(vp_x + (track_x + track_w - vp_x) * t)
            pygame.draw.line(screen, (60, 50, 90), (left_x, y_pos), (right_x, y_pos), 1)

    def _draw_hud(self, screen: pygame.Surface):
        # Score
        score_surf = self.font.render(f"Score: {self._score}", True, WHITE)
        screen.blit(score_surf, (SCREEN_WIDTH // 2 - score_surf.get_width() // 2, 18))

        # Speed bar
        bar_w = 200
        bar_x = SCREEN_WIDTH - bar_w - 20
        bar_y = 20
        speed_frac = (self._speed - INITIAL_SPEED) / (MAX_SPEED - INITIAL_SPEED)
        pygame.draw.rect(screen, (40, 30, 60), (bar_x, bar_y, bar_w, 18), border_radius=9)
        fill_w = int(bar_w * speed_frac)
        if fill_w > 0:
            # Color shifts red as speed increases
            sc = int(255 * speed_frac)
            bar_color = (sc, 255 - sc, 80)
            pygame.draw.rect(screen, bar_color, (bar_x, bar_y, fill_w, 18), border_radius=9)
        pygame.draw.rect(screen, NEON_CYAN, (bar_x, bar_y, bar_w, 18), width=2, border_radius=9)
        spd_label = self.small_font.render("SPEED", True, NEON_CYAN)
        screen.blit(spd_label, (bar_x, bar_y + 22))

        # Lane indicator dots
        dot_y = SCREEN_HEIGHT - 30
        dot_cx = SCREEN_WIDTH // 2
        for i in range(NUM_LANES):
            dx = dot_cx + (i - 1) * 30
            color = NEON_CYAN if i == self.player.lane else (60, 50, 90)
            pygame.draw.circle(screen, color, (dx, dot_y), 9)
            pygame.draw.circle(screen, WHITE, (dx, dot_y), 9, width=2)

        # Gesture hint
        hint = self.small_font.render("← Swipe Left / Right →", True, (150, 130, 200))
        screen.blit(hint, (20, SCREEN_HEIGHT - 30))

    def _draw_countdown(self, screen: pygame.Surface):
        elapsed  = (pygame.time.get_ticks() - self._countdown_t) / 1000
        time_left = max(0, 3 - elapsed)

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        if time_left > 0.3:
            num = str(int(math.ceil(time_left)))
            pulse = 1.0 + (math.ceil(time_left) - time_left) * 0.4
            surf  = self.big_font.render(num, True, NEON_CYAN)
            surf  = pygame.transform.rotozoom(surf, 0, pulse)
        else:
            surf = self.big_font.render("GO!", True, (100, 255, 80))

        screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2,
                           SCREEN_HEIGHT // 2 - surf.get_height() // 2))

        hint = self.font.render("Swipe LEFT or RIGHT to change lanes!", True, WHITE)
        screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT // 2 + 90))

    def _draw_crash_overlay(self, screen: pygame.Surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        p = ((pygame.time.get_ticks() - self._dead_t) / 1800)
        alpha = int(min(180, p * 200))
        overlay.fill((180, 20, 20, alpha))
        screen.blit(overlay, (0, 0))

        crash_surf = self.big_font.render("BUSTED!", True, WHITE)
        screen.blit(crash_surf, (SCREEN_WIDTH // 2 - crash_surf.get_width() // 2,
                                  SCREEN_HEIGHT // 2 - 60))
        score_surf = self.font.render(f"Score: {self._score}", True, NEON_CYAN)
        screen.blit(score_surf, (SCREEN_WIDTH // 2 - score_surf.get_width() // 2,
                                  SCREEN_HEIGHT // 2 + 40))

    def get_overlay_surface(self, frame: np.ndarray) -> pygame.Surface:
        overlay_frame = self.tracker.draw_landmarks_on_frame(frame.copy())
        overlay_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)
        surf = pygame.surfarray.make_surface(overlay_frame.swapaxes(0, 1))
        return pygame.transform.scale(surf, (320, 180))
