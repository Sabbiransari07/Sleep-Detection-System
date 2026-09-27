import cv2
from cvzone.FaceMeshModule import FaceMeshDetector
import pyfirmata
import csv
from datetime import datetime
import pyglet
import requests
import time

# ---------------- Telegram Setup ----------------
BOT_TOKEN = ""
CHAT_ID = ""

def send_whatsapp_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, data=data)
    except:
        print("Telegram message failed")

# ---------------- Camera Setup ----------------
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

FPS = cap.get(cv2.CAP_PROP_FPS)
if FPS == 0:
    FPS = 30

detector = FaceMeshDetector(maxFaces=1)

# ---------------- Thresholds ----------------
EYE_SLEEP_THRESHOLD = 0.23
MOUTH_YAWN_THRESHOLD = 35
SLEEP_TIME = int(FPS * 1.5)
YAWN_TIME = int(FPS * 2.0)

# ---------------- Counters ----------------
eye_counter = 0
yawn_counter = 0
sleep_state = False
yawn_state = False

# ✅ Accuracy Counters
total_frames = 0
sleep_detections = 0
yawn_detections = 0

# ---------------- Alarm ----------------
alarm = pyglet.media.load("alarm.mp3", streaming=False)

# ---------------- Arduino ----------------
pin = 7
try:
    board = pyfirmata.Arduino("COM5")
    pyfirmata.OUTPUT
    time.sleep(2)  # Allow time for Arduino to initialize
    board.digital[pin].write(1)
    arduino_ok = True
    motor_on = False
except:
    print("⚠ Arduino not connected")
    arduino_ok = False

# ---------------- CSV ----------------
def recordData(event):
    with open("database.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime("%d-%m-%Y %H:%M:%S"), event])

# ---------------- Alert Box ----------------
def alert(img, text):
    cv2.rectangle(img, (650, 20), (1250, 90), (0, 0, 255), cv2.FILLED)
    cv2.putText(img, text, (660, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 3)

# ---------------- Eye EAR Function ----------------
def eye_aspect_ratio(face, eye_ids):
    v1, _ = detector.findDistance(face[eye_ids[1]], face[eye_ids[5]])
    v2, _ = detector.findDistance(face[eye_ids[2]], face[eye_ids[4]])
    h,  _ = detector.findDistance(face[eye_ids[0]], face[eye_ids[3]])
    return (v1 + v2) / (2.0 * h)

# ---------------- Main Loop ----------------
while True:
    success, img = cap.read()
    if not success:
        break

    total_frames += 1

    img = cv2.flip(img, 1)
    img, faces = detector.findFaceMesh(img, draw=False)

    if faces:
        face = faces[0]

        LEFT_EYE  = [33, 160, 158, 133, 153, 144]
        RIGHT_EYE = [362, 385, 387, 263, 373, 380]

        upper_lip = 13
        lower_lip = 14
        mouth_left = 78
        mouth_right = 308

        leftEAR = eye_aspect_ratio(face, LEFT_EYE)
        rightEAR = eye_aspect_ratio(face, RIGHT_EYE)
        eye_avg = (leftEAR + rightEAR) / 2

        m_v, _ = detector.findDistance(face[upper_lip], face[lower_lip])
        m_h, _ = detector.findDistance(face[mouth_left], face[mouth_right])
        mouth_ratio = (m_v / m_h) * 100

        cv2.rectangle(img, (30, 20), (450, 180), (0, 255, 255), cv2.FILLED)
        cv2.putText(img, f"EAR: {eye_avg:.2f}", (40, 60),
                    cv2.FONT_HERSHEY_PLAIN, 2, (0,0,0), 2)
        cv2.putText(img, f"Mouth: {int(mouth_ratio)}", (40, 100),
                    cv2.FONT_HERSHEY_PLAIN, 2, (0,0,0), 2)

        # ✅ Live Accuracy Display
        if total_frames > 0:
            live_detection_rate = ((sleep_detections + yawn_detections) / total_frames) * 100
        else:
            live_detection_rate = 0

        cv2.putText(img, f"Live Accuracy: {live_detection_rate:.2f}%",
                    (40,40),
                    cv2.FONT_HERSHEY_PLAIN, 2, (0,0,0), 2)

        # -------- Sleep Detection --------
        if eye_avg < EYE_SLEEP_THRESHOLD:
            eye_counter += 1
            if eye_counter > SLEEP_TIME and not sleep_state:
                sleep_detections += 1
                alert(img, "SLEEP ALERT !!!")
                alarm.play()
                recordData("Sleep")
                send_whatsapp_alert("🚨 Sleep Alert Detected!")
                if arduino_ok:
                   board.digital[pin].write(0)   # Motor ON
                   motor_on = True
                sleep_state = True
        else:
            eye_counter = 0
            sleep_state = False
            if arduino_ok and motor_on:
                board.digital[pin].write(1)   # Motor OFF
                motor_on = False

        # -------- Yawn Detection --------
        if mouth_ratio > MOUTH_YAWN_THRESHOLD and eye_avg < 0.28:
            yawn_counter += 1
            if yawn_counter > YAWN_TIME and not yawn_state:
                yawn_detections += 1
                alert(img, "YAWN ALERT !!!")
                alarm.play()
                recordData("Yawn")
                send_whatsapp_alert("😴 Yawn Alert Detected!")
                yawn_state = True
        else:
            yawn_counter = 0
            yawn_state = False

        for id in LEFT_EYE + RIGHT_EYE + [upper_lip, lower_lip, mouth_left, mouth_right]:
            cv2.circle(img, face[id], 2, (0,0,255), cv2.FILLED)

    cv2.imshow("AI Drowsiness Detection", img)
    if cv2.waitKey(1) & 0xFF == 27:
        break

# Console Accuracy
print("\n===== SYSTEM PERFORMANCE =====")
print("Total Frames:", total_frames)
print("Sleep Detections:", sleep_detections)
print("Yawn Detections:", yawn_detections)

if total_frames > 0:
    detection_rate = ((sleep_detections + yawn_detections) / total_frames) * 100
    print(f"Detection Rate: {detection_rate:.2f}%")