'''=================================================

@Project -> File：Game->MAIN

@IDE：PyCharm

@coding: utf-8

@time:2022/6/19 15:36

@author:Pengzhangzhi

@Desc：
=================================================='''

import cv2
import pyautogui
import webbrowser
from time import time
import time as time_module
from math import hypot
from collections import deque
import mediapipe as mp
import matplotlib.pyplot as plt

# Initialize mediapipe pose class (Not used anymore, but keeping mp import setup)
mp_pose = mp.solutions.pose

# Initialize mediapipe hands class.
mp_hands = mp.solutions.hands
hands_video = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.75,
                            min_tracking_confidence=0.75)

# Initialize mediapipe drawing class.
mp_drawing = mp.solutions.drawing_utils


def detectPose(image, pose, draw=False):
    # Create a copy of the input image.
    output_image = image.copy()
    # Convert the image from BGR into RGB format.
    imageRGB = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # Perform the Pose Detection.
    results = pose.process(imageRGB)
    # Check if any landmarks are detected and are specified to be drawn.
    if results.pose_landmarks and draw:
        # Draw Pose Landmarks on the output image.
        mp_drawing.draw_landmarks(image=output_image, landmark_list=results.pose_landmarks,
                                  connections=mp_pose.POSE_CONNECTIONS)
    return output_image, results


def detectHands(image, hands, draw=False):
    output_image = image.copy()
    imageRGB = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(imageRGB)
    if results.multi_hand_landmarks and draw:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(image=output_image, landmark_list=hand_landmarks,
                                      connections=mp_hands.HAND_CONNECTIONS)
    return output_image, results


class BaseHandController:
    def __init__(self):
        self.COOLDOWN_SEC = 0.45
        self.last_action_time = 0.0
        self.last_action = "None"
        self.can_trigger = True
        self.AUTO_REARM_SEC = 0.55

    def _check_cooldown(self):
        now = time_module.time()
        if not self.can_trigger and (now - self.last_action_time >= self.AUTO_REARM_SEC):
            self.can_trigger = True
        return self.can_trigger and (now - self.last_action_time >= self.COOLDOWN_SEC)

    def trigger(self, action):
        self.last_action = action
        self.last_action_time = time_module.time()
        self.can_trigger = False
        return action

class IndexSwipeController:
    def __init__(self):
        # Settings (Suggested from 'earlier' model)
        self.HISTORY_SEC = 0.45
        self.COOLDOWN_SEC = 0.45
        self.DX_THRESH = 0.18
        self.DY_THRESH = 0.15
        self.NEUTRAL_RADIUS = 0.22
        self.NEUTRAL_HOLD = 0.08
        self.AUTO_REARM_SEC = 0.55
        
        # State
        self.history = deque() # (t, x, y)
        self.last_action_time = 0.0
        self.neutral_since = 0.0
        self.can_trigger = True
        self.last_cx, self.last_cy = 0.5, 0.5
        self.last_action = "None"

    def update(self, results):
        now = time_module.time()
        
        # Auto re-arm logic
        if not self.can_trigger and (now - self.last_action_time >= self.AUTO_REARM_SEC):
            self.can_trigger = True
            
        # Clean history
        while self.history and (now - self.history[0][0] > self.HISTORY_SEC):
            self.history.popleft()
            
        if not results or not results.multi_hand_landmarks:
            return None
            
        # Index fingertip (Landmark 8)
        lm = results.multi_hand_landmarks[0].landmark[8]
        cx, cy = lm.x, lm.y
        self.last_cx, self.last_cy = cx, cy
        self.history.append((now, cx, cy))
        
        # Neutral gating
        dist = hypot(cx - 0.5, cy - 0.5)
        if dist <= self.NEUTRAL_RADIUS:
            if self.neutral_since == 0.0:
                self.neutral_since = now
            elif now - self.neutral_since >= self.NEUTRAL_HOLD:
                self.can_trigger = True
        else:
            self.neutral_since = 0.0
            
        # Decide swipe if armed
        if self.can_trigger and (now - self.last_action_time >= self.COOLDOWN_SEC):
            action = self._detect_swipe()
            if action:
                self.last_action_time = now
                self.can_trigger = False
                self.last_action = action
                return action
        return None

    def _detect_swipe(self):
        if len(self.history) < 2:
            return None
        t0, x0, y0 = self.history[0]
        t1, x1, y1 = self.history[-1]
        dx, dy = x1 - x0, y1 - y0
        
        if abs(dx) >= abs(dy):
            if dx <= -self.DX_THRESH: return "left"
            if dx >= self.DX_THRESH: return "right"
        else:
            if dy <= -self.DY_THRESH: return "up"
            if dy >= self.DY_THRESH: return "down"
        return None

    def draw_hud(self, frame):
        h, w, _ = frame.shape
        # Draw Neutral Circle
        rad_px = int(self.NEUTRAL_RADIUS * min(w, h))
        cv2.circle(frame, (w//2, h//2), rad_px, (220, 220, 220), 2)
        # Fingertip marker
        cv2.circle(frame, (int(self.last_cx*w), int(self.last_cy*h)), 10, (255, 255, 255), 2)
        # Action indicator
        status_color = (0, 255, 0) if self.can_trigger else (0, 0, 255)
        cv2.putText(frame, f"READY: {self.can_trigger}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        if not self.can_trigger:
            cv2.putText(frame, f"LAST: {self.last_action.upper()}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        return frame

class ThumbPointController(BaseHandController):
    def __init__(self):
        super().__init__()
        self.THRESH = 0.08
        self.last_pointer = (0, 0) # dx, dy

    def update(self, results):
        if not results or not results.multi_hand_landmarks: return None
        if not self._check_cooldown(): return None

        lms = results.multi_hand_landmarks[0].landmark
        tip = lms[4] # Thumb Tip
        mcp = lms[2] # Thumb MCP
        
        dx, dy = tip.x - mcp.x, tip.y - mcp.y
        self.last_pointer = (dx, dy)

        if abs(dx) > abs(dy):
            if dx < -self.THRESH: return self.trigger("left")
            if dx > self.THRESH: return self.trigger("right")
        else:
            if dy < -self.THRESH: return self.trigger("up")
            if dy > self.THRESH: return self.trigger("down")
        return None

    def draw_hud(self, frame):
        h, w, _ = frame.shape
        cx, cy = w // 2, h // 2
        dx, dy = self.last_pointer
        cv2.line(frame, (cx, cy), (cx + int(dx*w*2), cy + int(dy*h*2)), (0, 255, 0), 4)
        cv2.circle(frame, (cx, cy), 5, (255, 255, 255), -1)
        return frame

class VelocityHandController(BaseHandController):
    def __init__(self):
        super().__init__()
        self.V_THRESH = 0.015
        self.history = deque(maxlen=5)
        self.last_v = (0, 0)

    def update(self, results):
        if not results or not results.multi_hand_landmarks: return None
        
        lms = results.multi_hand_landmarks[0].landmark
        palm_indices = [0, 5, 9, 13, 17]
        cx = sum(lms[i].x for i in palm_indices) / 5
        cy = sum(lms[i].y for i in palm_indices) / 5
        
        self.history.append((time_module.time(), cx, cy))
        if len(self.history) < 2: return None

        if not self._check_cooldown(): return None

        t0, x0, y0 = self.history[0]
        t1, x1, y1 = self.history[-1]
        dt = t1 - t0
        if dt == 0: return None
        
        vx, vy = (x1 - x0) / dt, (y1 - y0) / dt
        self.last_v = (vx * 0.05, vy * 0.05) # Scaled for HUD

        if hypot(vx, vy) > self.V_THRESH * 100: # Sensitivity scaling
            if abs(vx) > abs(vy):
                if vx < 0: return self.trigger("left")
                else: return self.trigger("right")
            else:
                if vy < 0: return self.trigger("up")
                else: return self.trigger("down")
        return None

    def draw_hud(self, frame):
        h, w, _ = frame.shape
        # Just show a motion vector in the center
        cx, cy = w//2, h//2
        vx, vy = self.last_v
        cv2.arrowedLine(frame, (cx, cy), (int(cx + vx*w), int(cy + vy*h)), (255, 0, 255), 3)
        return frame

# checkHandGestures is legacy and replaced by NeutralSwipeController
def checkHandGestures(image, results):
    return 'Center', 'Standing'


def detectPose(image, pose, draw=False):
    # Create a copy of the input image.
    output_image = image.copy()
    # Convert the image from BGR into RGB format.
    imageRGB = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    # Perform the Pose Detection.
    results = pose.process(imageRGB)
    # Check if any landmarks are detected and are specified to be drawn.
    if results.pose_landmarks and draw:
        # Draw Pose Landmarks on the output image.
        mp_drawing.draw_landmarks(image=output_image, landmark_list=results.pose_landmarks,
                                  connections=mp_pose.POSE_CONNECTIONS)
    return output_image, results


def detectHands(image, hands, draw=False):
    output_image = image.copy()
    imageRGB = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(imageRGB)
    if results.multi_hand_landmarks and draw:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(image=output_image, landmark_list=hand_landmarks,
                                      connections=mp_hands.HAND_CONNECTIONS)
    return output_image, results


def checkHandsJoined(image, results, draw=False, display=False):
    '''
    This function checks whether the hands of the person are joined or not in an image.
    Args:
        image:   The input image with a prominent person whose hands status (joined or not) needs to be classified.
        results: The output of the pose landmarks detection on the input image.
        draw:    A boolean value that is if set to true the function writes the hands status & distance on the output image.
        display: A boolean value that is if set to true the function displays the resultant image and returns nothing.
    Returns:
        output_image: The same input image but with the classified hands status written, if it was specified.
        hand_status:  The classified status of the hands whether they are joined or not.
    '''

    # Get the height and width of the input image.
    height, width, _ = image.shape

    # Create a copy of the input image to write the hands status label on.
    output_image = image.copy()

    # Get the left wrist landmark x and y coordinates.
    left_wrist_landmark = (results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST].x * width,
                           results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_WRIST].y * height)

    # Get the right wrist landmark x and y coordinates.
    right_wrist_landmark = (results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST].x * width,
                            results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST].y * height)

    # Calculate the euclidean distance between the left and right wrist.
    euclidean_distance = int(hypot(left_wrist_landmark[0] - right_wrist_landmark[0],
                                   left_wrist_landmark[1] - right_wrist_landmark[1]))

    # Compare the distance between the wrists with a appropriate threshold to check if both hands are joined.
    if euclidean_distance < 90:  # Scaled for 640x480 resolution

        # Set the hands status to joined.
        hand_status = 'Hands Joined'

        # Set the color value to green.
        color = (0, 255, 0)

    # Otherwise.
    else:

        # Set the hands status to not joined.
        hand_status = 'Hands Not Joined'

        # Set the color value to red.
        color = (0, 0, 255)

    # Check if the Hands Joined status and hands distance are specified to be written on the output image.
    if draw:
        # Write the classified hands status on the image.
        cv2.putText(output_image, f'{hand_status} (Dist: {euclidean_distance})', (10, 30), cv2.FONT_HERSHEY_PLAIN, 1, color, 2)

        # Write the threshold hint
        cv2.putText(output_image, f'Target: < 90', (10, 50),
                    cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 0), 2)

    # Check if the output image is specified to be displayed.
    if display:

        # Display the output image.
        plt.figure(figsize=[10, 10])
        plt.imshow(output_image[:, :, ::-1]);
        plt.title("Output Image");
        plt.axis('off');

    # Otherwise
    else:

        # Return the output image and the classified hands status indicating whether the hands are joined or not.
        return output_image, hand_status


def checkLeftRight(image, results):
    # Get the height and width of the image.
    height, width, _ = image.shape
    # Use NOSE for steering detection (body-based)
    nose_x = int(results.pose_landmarks.landmark[mp_pose.PoseLandmark.NOSE].x * width)
    
    # Dead zone in the middle (e.g., 20% of width)
    margin = width // 8
    center = width // 2
    
    if nose_x < center - margin:
        return 'Left'
    elif nose_x > center + margin:
        return 'Right'
    else:
        return 'Center'


def checkJumpCrouch(image, results, MID_Y):
    # Natural body jump/crouch based on shoulder vertical position
    height, width, _ = image.shape
    left_y = int(results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER].y * height)
    right_y = int(results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_SHOULDER].y * height)
    shoulder_mid_y = (right_y + left_y) // 2
    
    # Sensitivity threshold (e.g., 40 pixels for jump/crouch)
    threshold = 40
    
    if shoulder_mid_y < MID_Y - threshold:
        return 'Jumping'
    elif shoulder_mid_y > MID_Y + threshold:
        return 'Crouching'
    else:
        return 'Standing'


def checkHandGestures(image, results):
    if not results or not results.multi_hand_landmarks:
        return 'Center', 'Standing'

    horiz_pos = 'Center'
    vert_pos = 'Standing'
    
    for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
        # Only use the RIGHT hand as requested
        label = results.multi_handedness[i].classification[0].label
        if label != 'Right':
            continue
            
        # Count extended fingers (Index, Middle, Ring, Pinky)
        extended = []
        for tip_id, mcp_id, name in [(8, 5, 'Index'), (12, 9, 'Middle'), (16, 13, 'Ring'), (20, 17, 'Pink')]:
            # Back of palm to webcam: check if tip is higher than base
            if hand_landmarks.landmark[tip_id].y < hand_landmarks.landmark[mcp_id].y:
                extended.append(name)
        
        count = len(extended)

        # User Specific Mapping:
        # 1 finger (Index) -> Left
        if count == 1 and 'Index' in extended:
            horiz_pos = 'Left'
        # 2 fingers (Index + Middle) -> Right
        elif count == 2 and 'Index' in extended and 'Middle' in extended:
            horiz_pos = 'Right'
        # 3 fingers (Index + Middle + Ring) -> Jump
        elif count == 3:
            vert_pos = 'Jumping'
        # 4 fingers (All 4) -> Roll
        elif count == 4:
            vert_pos = 'Crouching'
            
    return horiz_pos, vert_pos


def run():
    # Automatically open the game in the browser
    webbrowser.open("https://poki.com/en/g/subway-surfers")

    camera_video = cv2.VideoCapture(0)
    camera_video.set(3, 640)
    camera_video.set(4, 480)

    win_name = 'Subway Surfers Gesture Overlay'
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    try:
        cv2.setWindowProperty(win_name, cv2.WND_PROP_TOPMOST, 1)
    except:
        pass

    sw, sh = pyautogui.size()
    ww, wh = 320, 240
    cv2.resizeWindow(win_name, ww, wh)
    cv2.moveWindow(win_name, sw - ww - 20, 20)

    # App States: 'HAND_MODE_SELECTION', 'CALIBRATION', 'PLAYING'
    app_state = 'HAND_MODE_SELECTION'
    hand_controller_mode = None # 'INDEX', 'THUMB', 'VELOCITY'
    
    game_started = False
    last_hand_gesture = ('Center', 'Standing')
    
    # Initialize the controller placeholder
    swipe_controller = None

    while camera_video.isOpened():
        ok, frame = camera_video.read()
        if not ok: continue
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        k = cv2.waitKey(1) & 0xFF
        if k == 27: break

        # ── State Machine ──────────────────────────────────────────────────
        if app_state == 'HAND_MODE_SELECTION':
            cv2.putText(frame, 'SELECT HAND CONTROLLER', (w//2 - 140, h//2 - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, '1. INDEX FINGER (Circle)', (w//2 - 100, h//2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, '2. THUMB POINTING', (w//2 - 100, h//2 + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, '3. HAND VELOCITY (Swiping)', (w//2 - 100, h//2 + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            
            if k == ord('1'):
                hand_controller_mode = 'INDEX'
                swipe_controller = IndexSwipeController()
                app_state = 'CALIBRATION'
            elif k == ord('2'):
                hand_controller_mode = 'THUMB'
                swipe_controller = ThumbPointController()
                app_state = 'CALIBRATION'
            elif k == ord('3'):
                hand_controller_mode = 'VELOCITY'
                swipe_controller = VelocityHandController()
                app_state = 'CALIBRATION'

        elif app_state == 'CALIBRATION':
            cv2.putText(frame, 'CALIBRATION', (w//2 - 60, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(frame, f'MODE: {hand_controller_mode}', (w//2 - 60, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, 'Press SPACE to Start', (w//2 - 90, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            frame, results = detectHands(frame, hands_video, draw=True)
            if results and results.multi_hand_landmarks and k == ord(' '):
                app_state = 'PLAYING'
                game_started = True
                # Critical Fix: Auto-focus the browser by clicking the center of the screen
                try:
                    pyautogui.click(sw//2, sh//2)
                except:
                    pass

        elif app_state == 'PLAYING':
            frame, results = detectHands(frame, hands_video, draw=False)
            if swipe_controller:
                action = swipe_controller.update(results)
                frame = swipe_controller.draw_hud(frame)
                
                if action:
                    pyautogui.press(action)
                
                # Also draw general status
                status_color = (0, 255, 0) if swipe_controller.can_trigger else (0, 0, 255)
                cv2.putText(frame, f"{hand_controller_mode} READY: {swipe_controller.can_trigger}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
                if not swipe_controller.can_trigger:
                    cv2.putText(frame, f"LAST: {swipe_controller.last_action.upper()}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            # Resume key (Space)
            if k == ord(' '):
                pyautogui.press('space')

            cv2.putText(frame, f'FPS: {int(camera_video.get(cv2.CAP_PROP_FPS))}', (10, h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        cv2.imshow(win_name, frame)

    camera_video.release()
    cv2.destroyAllWindows()


# https://www.kiloo.com/subway-surfers/
if __name__ == '__main__':
    run()
