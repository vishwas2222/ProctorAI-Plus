#!/usr/bin/env python3
"""
ProctorAI Client - ✨ Argument-Aware ✨
This version is designed to be launched for a specific exam session.

It now accepts command-line arguments for:
--username (e.g., 'student1')
--exam_id (e.g., '3')

It constructs a session_id in the format: 'exam_{exam_id}_{username}_{timestamp}'
"""

import warnings
warnings.filterwarnings("ignore")

import os
import platform
import subprocess
import sys
import time
import threading
from collections import deque
from datetime import datetime
import queue
import requests
import urllib.request
import argparse # ✨ NEW IMPORT

import cv2
import numpy as np
import torch
import speech_recognition as sr
from ultralytics import YOLO

import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision.face_landmarker import FaceLandmarkerResult

# =====================================
# 🔹 Configuration & Models
# =====================================
SERVER_URL = "http://127.0.0.1:5000/log_data"

# ✨ NEW: Argument Parsing
parser = argparse.ArgumentParser(description="ProctorAI Client Agent")
parser.add_argument('--username', type=str, required=True, help="The student's username")
parser.add_argument('--exam_id', type=str, required=True, help="The unique ID for this exam")
args = parser.parse_args()

# ✨ MODIFIED: Use args to set constants
STUDENT_ID = args.username  # This is the username string
EXAM_ID = args.exam_id
SESSION_ID = f"exam_{EXAM_ID}_{STUDENT_ID}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print(f"[🚀] Initializing ProctorAI Agent...")
print(f"    Student: {STUDENT_ID}")
print(f"    Exam ID: {EXAM_ID}")
print(f"    Session ID: {SESSION_ID}")


# Ensure we operate from the client-agent directory so relative model paths resolve predictably
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    os.chdir(SCRIPT_DIR)
except Exception:
    # best-effort: not fatal
    pass

LANDMARKER_TASK_FILE = "face_landmarker.task"
if not os.path.exists(LANDMARKER_TASK_FILE):
    print(f"Downloading {LANDMARKER_TASK_FILE}...")
    try:
        url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        urllib.request.urlretrieve(url, LANDMARKER_TASK_FILE)
        print("Download complete.")
    except Exception as e:
        print(f"[❌] Error: Could not download {LANDMARKER_TASK_FILE}. {e}")
        sys.exit(1)

# Resolve the landmark task file to an absolute path and normalize for MediaPipe
from pathlib import Path
LANDMARKER_TASK_PATH = str(Path(LANDMARKER_TASK_FILE).resolve())
print(f"[ℹ️] Using face landmarker task file: {LANDMARKER_TASK_PATH}")

# ... (YOLO and MediaPipe initializations are unchanged) ...
yolo_model = None
try:
    yolo_model = YOLO("yolov8n.pt")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if yolo_model:
        yolo_model.to(device)
except Exception as e:
    print(f"[⚠️] Warning: Could not load YOLO model: {e}")

mp_hands = mp.solutions.hands.Hands(max_num_hands=2, min_detection_confidence=0.7)
mp_holistic = mp.solutions.holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# =====================================
# 🔹 Global Flags & Dynamic Thresholds
# =====================================
# ... (all global flags and thresholds are unchanged) ...
running = True
data_to_send = queue.Queue()
voice_active = False
last_voice_time = 0.0
face_data = {"count": 0, "turned_away": False, "no_face": False, "eye_alert": False, "blink": 0, "eye_velocity": 0.0, "emotion": "N/A"}
hand_alert = False
yolo_results = None
gesture_alert = False
face_lock = threading.Lock()
yolo_lock = threading.Lock()
hand_lock = threading.Lock()
gesture_lock = threading.Lock()
voice_lock = threading.Lock()  # ✨ ADDED
last_spoken_text = ""        # ✨ ADDED
current_alerts = set()
gaze_history = deque(maxlen=5)
DYNAMIC_THRESHOLDS = {"head_yaw": 15.0, "gaze_min": 0.35, "gaze_max": 0.65, "ear": 0.21}
environment_status = "Calibrating..."
EAR_CONSEC_FRAMES = 3
blink_counter = 0
total_blinks = 0
SILENCE_TIMEOUT = 4

# =====================================
# 🔹 Adaptive Fairness Calibration
# =====================================
def calibrate_environment(cap, num_frames=60):
    # ... (function is unchanged) ...
    global environment_status
    print("[🔬] Starting environment calibration...")
    brightness_vals, contrast_vals = [], []
    for i in range(num_frames):
        ret, frame = cap.read()
        if not ret: continue
        cv2.putText(frame, f"Calibrating... {i+1}/{num_frames}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.imshow("ProctorAI Client", frame)
        cv2.waitKey(1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness_vals.append(gray.mean())
        contrast_vals.append(gray.std())
        time.sleep(0.05)
    avg_brightness = np.mean(brightness_vals)
    if avg_brightness < 70:
        environment_status = "Dark Environment: Adjusting sensitivity."
        DYNAMIC_THRESHOLDS["head_yaw"] = 20.0
        DYNAMIC_THRESHOLDS["gaze_min"] = 0.30
        DYNAMIC_THRESHOLDS["gaze_max"] = 0.70
        DYNAMIC_THRESHOLDS["ear"] = 0.19
    elif avg_brightness > 180:
        environment_status = "Bright Environment: Using standard sensitivity."
    else:
        environment_status = "Optimal Environment: Standard sensitivity."
    print(f"[✅] Calibration complete. Status: {environment_status}")
    print(f" - Avg Brightness: {avg_brightness:.2f}")

# =====================================
# 🔹 Helper functions
# =====================================
def beep_once():
    # ... (function is unchanged) ...
    try:
        if platform.system() == "Windows":
            import winsound
            winsound.Beep(900, 300)
            return
    except Exception: pass
    sound_candidates = [
        ("/usr/share/sounds/freedesktop/stereo/complete.oga", "paplay"),
        ("/usr/share/sounds/freedesktop/stereo/complete.wav", "paplay"),
        ("/usr/share/sounds/alsa/Front_Center.wav", "aplay"),
    ]
    for path, player in sound_candidates:
        if os.path.exists(path):
            try:
                subprocess.run([player, path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception: continue
    if platform.system() == "Darwin":
        for path in ["/System/Library/Sounds/Glass.aiff", "/System/Library/Sounds/Pop.aiff"]:
            if os.path.exists(path):
                try:
                    subprocess.run(["afplay", path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except Exception: pass
    sys.stdout.write("\a")
    sys.stdout.flush()

def eye_aspect_ratio(landmarks):
    # ... (function is unchanged) ...
    def dist(p1, p2):
        return np.linalg.norm([p1.x - p2.x, p1.y - p2.y, p1.z - p2.z])
    left_p1, left_p2, left_p3, left_p4 = landmarks[160], landmarks[144], landmarks[158], landmarks[153]
    left_p5, left_p6 = landmarks[33], landmarks[133]
    ear_left = (dist(left_p1, left_p2) + dist(left_p3, left_p4)) / (2.0 * dist(left_p5, left_p6))
    right_p1, right_p2, right_p3, right_p4 = landmarks[387], landmarks[373], landmarks[385], landmarks[380]
    right_p5, right_p6 = landmarks[263], landmarks[362]
    ear_right = (dist(right_p1, right_p2) + dist(right_p3, right_p4)) / (2.0 * dist(right_p5, right_p6))
    return (ear_left + ear_right) / 2.0

def map_blendshapes_to_emotion(blendshapes):
    # ... (function is unchanged) ...
    if not blendshapes: return "N/A"
    scores = {b.category_name: b.score for b in blendshapes}
    if scores.get("mouthSmileLeft", 0) > 0.5 or scores.get("mouthSmileRight", 0) > 0.5: return "Happy"
    if scores.get("mouthFrownLeft", 0) > 0.4 or scores.get("mouthFrownRight", 0) > 0.4: return "Sad"
    if scores.get("jawOpen", 0) > 0.5 and scores.get("eyeWideLeft", 0) > 0.4: return "Surprised"
    if scores.get("browDownLeft", 0) > 0.5 or scores.get("browDownRight", 0) > 0.5: return "Angry"
    if scores.get("mouthPucker", 0) > 0.5: return "Neutral"
    return "Neutral"

# =====================================
# 🔹 Worker Threads
# =====================================
def send_data_thread():
    # ... (function is unchanged) ...
    while running:
        try:
            payload = data_to_send.get(timeout=1)
            requests.post(SERVER_URL, json=payload, timeout=5)
        except queue.Empty:
            continue
        except requests.exceptions.RequestException as e:
            print(f"[Network] Connection error: {e}")
        except Exception as e:
            print(f"[Network] An unexpected error occurred: {e}")

last_alert_state = False
def beep_thread():
    # ... (function is unchanged) ...
    global last_alert_state, yolo_results
    while running:
        with face_lock:
            alert_state = face_data["turned_away"] or face_data["eye_alert"] or face_data["no_face"]
        alert_state = alert_state or hand_alert or gesture_alert
        if yolo_model and yolo_results:
            with yolo_lock:
                try:
                    boxes_data = getattr(yolo_results.boxes, "data", yolo_results.boxes.xyxy)
                    rows = boxes_data.tolist()
                    for r in rows:
                        conf, cls = r[4], r[5]
                        cls_name = yolo_model.names[int(cls)]
                        if cls_name in ["cell phone", "laptop"] and float(conf) > 0.7:
                            alert_state = True
                            break
                except Exception: pass
        if alert_state and not last_alert_state:
            beep_once()
        last_alert_state = alert_state
        time.sleep(0.12)

def start_voice_listener():
    # ... (function is unchanged) ...
    global voice_active, last_voice_time
    try:
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
        
        def callback(recognizer_inst, audio):
            global voice_active, last_voice_time, last_spoken_text # ✨ MODIFIED
            try:
                text = recognizer_inst.recognize_google(audio)
                if text and text.strip():
                    voice_active = True
                    last_voice_time = time.time()
                    with voice_lock: # ✨ ADDED
                        last_spoken_text = text # ✨ ADDED
                    print(f"[Voice] Detected: {text}")
            except Exception: pass
        
        return recognizer.listen_in_background(mic, callback)
    
    except Exception as e:
        print(f"[⚠️] Microphone not available: {e}")
        return lambda wait_for_stop=True: None

def yolo_thread(frame_getter):
    # ... (function is unchanged) ...
    global yolo_results
    if not yolo_model: return
    frame_skip = 3
    count = 0
    while running:
        frame = frame_getter()
        if frame is None:
            time.sleep(0.05)
            continue
        count += 1
        if count % frame_skip != 0:
            time.sleep(0.03)
            continue
        try:
            results = yolo_model(cv2.resize(frame, (320, 240)), verbose=False)
            if results:
                with yolo_lock:
                    yolo_results = results[0]
        except Exception:
            with yolo_lock:
                yolo_results = None
        time.sleep(0.05)

def face_landmarker_thread(frame_getter):
    # ... (function is unchanged) ...
    global face_data, hand_alert, gaze_history, blink_counter, total_blinks
    no_face_start = None
    BaseOptions = mp_tasks.BaseOptions
    FaceLandmarkerOptions = mp_tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp_tasks.vision.RunningMode
    # Prefer passing an absolute, resolved path. If that fails, try a file:// URI, then a buffer.
    tried = []
    created = False
    # 1) Try with resolved absolute path
    try:
        options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=LANDMARKER_TASK_PATH),
            running_mode=VisionRunningMode.VIDEO,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=3
        )
        landmarker = vision.FaceLandmarker.create_from_options(options)
        created = True
    except Exception as e:
        tried.append(('abs', LANDMARKER_TASK_PATH, str(e)))
    # 2) Try file:// URI form (some Windows/Mediapipe builds prefer this)
    if not created:
        try:
            uri = Path(LANDMARKER_TASK_PATH).as_uri()
            options = FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=uri),
                running_mode=VisionRunningMode.VIDEO,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
                num_faces=3
            )
            landmarker = vision.FaceLandmarker.create_from_options(options)
            created = True
        except Exception as e:
            tried.append(('uri', uri, str(e)))
    # 3) Try reading bytes and passing buffer (best-effort fallback)
    if not created:
        try:
            with open(LANDMARKER_TASK_PATH, 'rb') as f:
                buf = f.read()
            options = FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_buffer=buf),
                running_mode=VisionRunningMode.VIDEO,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
                num_faces=3
            )
            landmarker = vision.FaceLandmarker.create_from_options(options)
            created = True
        except Exception as e:
            tried.append(('buffer', LANDMARKAR_TASK_PATH, str(e)))

    if not created:
        print(f"[❌] Failed to create FaceLandmarker. Attempts:\n{tried}")
        return
    frame_timestamp_ms = 0
    while running:
        frame = frame_getter()
        if frame is None:
            time.sleep(0.05)
            continue
        ih, iw = frame.shape[:2]
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        frame_timestamp_ms = int(time.time() * 1000)
        try:
            results: FaceLandmarkerResult = landmarker.detect_for_video(mp_image, frame_timestamp_ms)
        except Exception:
            continue
        with face_lock:
            face_data["eye_velocity"] = 0.0
            if results and results.face_landmarks:
                face_data["count"] = len(results.face_landmarks)
                face_data.update({"turned_away": False, "no_face": False, "eye_alert": False})
                first_face_landmarks = results.face_landmarks[0]
                if results.facial_transformation_matrixes:
                    matrix = results.facial_transformation_matrixes[0]
                    head_yaw = np.degrees(np.arcsin(-matrix[2][0]))
                    if abs(head_yaw) > DYNAMIC_THRESHOLDS["head_yaw"]:
                        face_data["turned_away"] = True
                li, ri = first_face_landmarks[468], first_face_landmarks[473]
                gaze_x = (li.x + ri.x) / 2
                gaze_history.append(gaze_x)
                if len(gaze_history) > 1:
                    face_data["eye_velocity"] = float(np.mean(np.abs(np.diff(list(gaze_history)))))
                if not (DYNAMIC_THRESHOLDS["gaze_min"] < gaze_x < DYNAMIC_THRESHOLDS["gaze_max"]):
                    face_data["eye_alert"] = True
                ear_val = eye_aspect_ratio(first_face_landmarks)
                if ear_val < DYNAMIC_THRESHOLDS["ear"]:
                    blink_counter += 1
                else:
                    if blink_counter >= EAR_CONSEC_FRAMES:
                        total_blinks += 1
                    blink_counter = 0
                if results.face_blendshapes:
                    face_data["emotion"] = map_blendshapes_to_emotion(results.face_blendshapes[0])
                no_face_start = None
            else:
                if no_face_start is None:
                    no_face_start = time.time()
                elif time.time() - no_face_start > 2:
                    face_data.update({"count": 0, "turned_away": False, "no_face": True, "eye_alert": False, "emotion": "N/A"})
                else:
                    face_data.update({"count": 0, "turned_away": False, "no_face": False, "eye_alert": False, "emotion": "N/A"})
        small_rgb = cv2.cvtColor(cv2.resize(frame, (320, 240)), cv2.COLOR_BGR2RGB)
        try:
            results_hands = mp_hands.process(small_rgb)
            with hand_lock:
                hand_alert = False
                if results_hands and results_hands.multi_hand_landmarks:
                    for hand_landmarks in results_hands.multi_hand_landmarks:
                        if hand_landmarks.landmark[8].y * ih > ih * 0.6:
                            hand_alert = True
                            break
        except Exception:
            with hand_lock:
                hand_alert = False
        time.sleep(0.05)

def holistic_thread(frame_getter):
    # ... (function is unchanged) ...
    global gesture_alert
    while running:
        frame = frame_getter()
        if frame is None: time.sleep(0.05); continue
        try:
            results = mp_holistic.process(cv2.cvtColor(cv2.resize(frame, (320, 240)), cv2.COLOR_BGR2RGB))
        except Exception: continue
        with gesture_lock:
            gesture_alert = False
            try:
                if results and (results.left_hand_landmarks or results.right_hand_landmarks):
                    all_landmarks = (results.left_hand_landmarks.landmark if results.left_hand_landmarks else []) + \
                                    (results.right_hand_landmarks.landmark if results.right_hand_landmarks else [])
                    if any(lm.y > 0.6 for lm in all_landmarks):
                        gesture_alert = True
            except Exception: pass
        time.sleep(0.05)

# =====================================
# 🔹 Main Program Execution
# =====================================
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("[❌] Error: Could not open camera. Exiting.")
    sys.exit(1)

calibrate_environment(cap)
current_frame = None
def get_frame(): return current_frame.copy() if current_frame is not None else None

print("[🚀] Starting all threads...")
stop_listen = start_voice_listener()
threading.Thread(target=send_data_thread, daemon=True).start()
threading.Thread(target=beep_thread, daemon=True).start()
threading.Thread(target=yolo_thread, args=(get_frame,), daemon=True).start()
threading.Thread(target=face_landmarker_thread, args=(get_frame,), daemon=True).start()
threading.Thread(target=holistic_thread, args=(get_frame,), daemon=True).start()

print("[🎥] Camera started... Press 'q' in the OpenCV window to quit.")

try:
    while running:
        ret, frame = cap.read()
        if not ret:
            print("[⚠️] Frame read failed, stopping.")
            break
        current_frame = frame.copy()
        current_alerts.clear()

        # ... (Alert aggregation logic is unchanged) ...
        with face_lock:
            is_talking = voice_active or (time.time() - last_voice_time < SILENCE_TIMEOUT)
            distraction = (face_data["turned_away"] or face_data["eye_alert"]) and is_talking
            if face_data["count"] > 1: current_alerts.add("Multiple faces detected!")
            elif distraction: current_alerts.add("Distraction: Looking away while talking")
            elif face_data["no_face"]: current_alerts.add("No person detected!")
            
            # ✨ MODIFIED BLOCK
            if is_talking: 
                current_alerts.add("Someone is talking!")
                with voice_lock:
                    if last_spoken_text:
                        # Add the actual spoken text as an alert
                        current_alerts.add(f"VOICE: {last_spoken_text}")
                        last_spoken_text = "" # Clear it so it's not sent again
        
        annotated = frame.copy()

        with yolo_lock:
            results_yolo = yolo_results
            if results_yolo and yolo_model:
                try:
                    scale_x, scale_y = frame.shape[1] / 320, frame.shape[0] / 240
                    boxes = getattr(results_yolo.boxes, "data", results_yolo.boxes.xyxy).tolist()
                    for r in boxes:
                        x1, y1, x2, y2, conf, cls_id = r[:6]
                        cls_name = yolo_model.names[int(cls_id)]
                        if cls_name in ["cell phone", "laptop"] and conf > 0.7:
                            current_alerts.add(f"{cls_name.upper()} detected!")
                            cv2.rectangle(annotated, (int(x1*scale_x), int(y1*scale_y)), (int(x2*scale_x), int(y2*scale_y)), (0,255,0), 2)
                except Exception: pass
        
        with hand_lock:
            if hand_alert: current_alerts.add("Hand on mouse/keyboard detected!")
        with gesture_lock:
            if gesture_alert: current_alerts.add("Suspicious micro gesture detected!")

        # --- ✨ MODIFIED: Package and send data ---
        with face_lock:
            metrics_payload = face_data.copy()
            metrics_payload['total_blinks'] = total_blinks
            metrics_payload['source'] = 'python-client' # Identify source

        payload = {
            "student_id": STUDENT_ID,   # This is the username (e.g., 'student1')
            "session_id": SESSION_ID,   # The new session ID (e.g., 'exam_3_student1_...')
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "alerts": sorted(list(current_alerts)),
            "metrics": metrics_payload
        }
        data_to_send.put(payload)

        # --- Draw Overlays (unchanged) ---
        y_offset = 60
        # ✨ MODIFIED: Display all alerts, even long voice ones (they will be truncated)
        for alert_text in sorted(list(current_alerts)):
            display_text = alert_text[:70] + '...' if len(alert_text) > 70 else alert_text
            cv2.putText(annotated, f"⚠️ {display_text}", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            y_offset += 40
            
        with face_lock:
            emotion_text = f"Emotion: {face_data['emotion']}"
            cv2.putText(annotated, emotion_text, (annotated.shape[1] - 250, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
            cv2.putText(annotated, f"Faces: {face_data['count']}", (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(annotated, f"Blinks: {total_blinks}", (20, y_offset + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(annotated, f"Gaze Vel: {face_data['eye_velocity']:.3f}", (20, y_offset + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(annotated, environment_status, (10, annotated.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow("ProctorAI Client", annotated)

        if voice_active and (time.time() - last_voice_time > SILENCE_TIMEOUT):
            voice_active = False
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
except KeyboardInterrupt:
    print("\n[🛑] Interrupted by user.")
finally:
    running = False
    print("[⚙️] Shutting down...")
    if 'stop_listen' in locals() and stop_listen:
        stop_listen(wait_for_stop=False)
    cap.release()
    cv2.destroyAllWindows()
    time.sleep(0.5)
    print("[🛑] Program ended.")