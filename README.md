# GestureArcade 🖐️

**GestureArcade** is a hand-gesture-controlled gaming platform built with Python. Using only your webcam and your hands, you can play a collection of mini-games — no controller or mouse required.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running the App](#running-the-app)
- [Games](#games)
- [Controls](#controls)
- [Project Structure](#project-structure)
- [Configuration](#configuration)

---

## Features

- Real-time hand tracking powered by **MediaPipe**
- Smooth landmark filtering via the **One Euro Filter** algorithm
- Four fully playable games accessible from a central hub
- Picture-in-picture gesture overlay during gameplay
- Gesture-based exit: hover your hand over the exit zone to return to the hub
- Selfie capture with batch email delivery

---

## Requirements

- Python 3.9 or higher
- A working webcam
- The packages listed in `requirements.txt`:

| Package | Minimum Version |
|---|---|
| `mediapipe` | 0.10.0 |
| `pygame` | 2.5.0 |
| `opencv-python` | 4.8.0 |
| `numpy` | 1.24.0 |

> **Subway Surfer** additionally requires `pyautogui` and `matplotlib` (used by its standalone script).

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/whysist/gestureGames.git
cd gestureGames

# 2. (Optional) Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the App

```bash
python main.py
```

The application opens a **1280 × 720** window. Point your webcam at yourself and use the hub to launch any game.

> **Camera switching:** Press **`C`** at any time to cycle through available cameras.

---

## Games

> `main.py` loads four games from the `games/` folder. Additional games exist in the codebase but are not yet wired into the hub.

### 1. 🏓 Gesture Pong
Move your **index finger up and down** to control your paddle. Beat the AI opponent to 7 points to win. Ball speed increases with every volley and over time.

| Detail | Value |
|---|---|
| Winning score | 7 points |
| Input | Index finger vertical position |

### 2. 📸 Point Selfie
A face-mesh AR experience. Your live camera feed is overlaid with a real-time facial landmark skeleton. Take photos during a session and send them to yourself by email at the end.

| Action | How |
|---|---|
| Take a photo | Click the **PHOTO** button |
| End session & email | Click the **DONE** button, then enter your email address |
| Saved photos | `captures/` folder |

### 3. 🏃 Subway Surfer
A gesture-controlled runner. **Swipe your hand left or right** to change lanes and dodge oncoming trains. Speed increases over time.

| Detail | Value |
|---|---|
| Lanes | 3 |
| Input | Horizontal hand swipe |

> This game runs as a **separate subprocess** and opens its own window. Close it with **ESC** to return to the hub.

### 4. 🧱 Brick Breaker
Classic brick-breaking action. Move your **index finger left and right** to steer the paddle. Yellow bricks spawn an extra ball when destroyed. Lose all balls and the game ends.

| Detail | Value |
|---|---|
| Extra ball | Destroy a yellow brick |
| Input | Index finger horizontal position |

---

## Controls

| Key / Action | Effect |
|---|---|
| `ESC` | Return to hub (while in a game) / Quit (from hub) |
| `C` | Cycle to the next camera |
| `1` / `2` / `3` / `4` | Launch Pong / Selfie / Subway Surfer / Brick Breaker from hub |
| Click a hub card | Launch the selected game |
| Hover hand over exit zone | Gesture-based return to hub |

---

## Project Structure

```
gestureGames/
├── main.py                  # Entry point — hub loop and game dispatch
├── config.py                # Global constants (resolution, colors, tuning values)
├── requirements.txt
│
├── gesture/                 # Hand & face tracking layer
│   ├── tracker.py           # HandTracker — MediaPipe wrapper with smoothing
│   ├── face_tracker.py      # FaceTracker — MediaPipe Face Mesh wrapper
│   ├── filters.py           # One Euro Filter implementation
│   └── predictor.py         # Constant-velocity motion predictor
│
├── ui/                      # UI utilities
│   ├── hub.py               # Main menu / game selector
│   ├── text_input.py        # On-screen keyboard input widget
│   └── email_utils.py       # SMTP email helper (batch selfie delivery)
│
├── games/                   # All mini-game implementations
│   ├── base_game.py         # Abstract BaseGame class
│   ├── pong/                # ✅ Gesture Pong (active)
│   ├── selfie/              # ✅ Point Selfie (active)
│   ├── subway-surfer/       # ✅ Subway Surfer (active, standalone subprocess)
│   ├── breakout/            # ✅ Brick Breaker (active)
│   ├── ninja/               # 🔧 Fruit Ninja (not yet in hub)
│   ├── flappy/              # 🔧 Flappy Bird (not yet in hub)
│   ├── drum/                # 🔧 Air Drums (not yet in hub)
│   └── ar_companion/        # 🔧 AR Companion (not yet in hub)
│
└── assets/                  # Static assets (images, sounds)
```

---

## Configuration

All tuneable parameters live in `config.py`:

- **Display:** `SCREEN_WIDTH`, `SCREEN_HEIGHT`, `FPS`
- **MediaPipe:** detection/tracking confidence, number of hands, model complexity
- **Smoothing:** One Euro Filter `min_cutoff` and `beta` values
- **Per-game tuning:** paddle speed, ball speed, surfer spawn rate, drum thresholds, etc.
- **Email:** SMTP settings read from environment variables `GMAIL_USER` and `GMAIL_PASS`

To configure email sending, create a `.env` file in the project root:

```
GMAIL_USER=your_address@gmail.com
GMAIL_PASS=your_app_password
```

> Use a [Gmail App Password](https://support.google.com/accounts/answer/185833) — not your regular account password.
