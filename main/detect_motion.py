from datetime import datetime, timezone
import random
import time

import firebase_admin
from firebase_admin import credentials, firestore
from sense_hat import SenseHat


SERVICE_ACCOUNT_PATH = "doorwatch-1d0ff-firebase-adminsdk-fbsvc-92eec4b22c.json"
DEVICE_ID = "doorwatch-main"

# Mock motion settings
MOCK_MODE = True
MOTION_CHANCE = 0.3   # 30% chance of motion each loop
LOOP_DELAY = 5        # seconds between checks

sense = SenseHat()


def init_firestore():
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
    return firestore.client()


def get_sensor_readings() -> dict:
    """
    Reads current environmental data from the Sense HAT.
    """
    return {
        "temperature": round(sense.get_temperature(), 2),
        "humidity": round(sense.get_humidity(), 2),
    }

def get_device_settings(db) -> dict:
    """
    Reads the current device settings from Firestore.
    """
    settings_ref = db.collection("devices").document(DEVICE_ID).collection("settings").document("config")
    snapshot = settings_ref.get()

    if not snapshot.exists:
        return {
            "mode": "visitor",
            "status": "offline",
            "emailAlertsEnabled": False,
            "securityAlarmEnabled": False,
        }

    return snapshot.to_dict()


def get_mock_motion_detection() -> bool:
    """
    Simulates PIR motion detection.
    """
    if not MOCK_MODE:
        return False
    return random.random() < MOTION_CHANCE


def send_detection(db, sensor_data: dict, motion_detected: bool):
    detection = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "createdAt": firestore.SERVER_TIMESTAMP,
        "mode": "visitor",
        "temperature": sensor_data["temperature"],
        "humidity": sensor_data["humidity"],
        "motionDetected": motion_detected,
        "imageUrl": "",
        "emailSent": False,
        "alarmTriggered": False,
        "source": "raspberry-pi-mock-pir"
    }

    detections_ref = db.collection("devices").document(DEVICE_ID).collection("detections")
    doc_ref = detections_ref.add(detection)

    print("Detection sent successfully.")
    print(f"Document ID: {doc_ref[1].id}")
    print(detection)


def main():
    db = init_firestore()
    print("DoorWatch running with mock PIR detections...")

    while True:
        sensor_data = get_sensor_readings()
        print(f"Current readings -> Temp: {sensor_data['temperature']}°C, Humidity: {sensor_data['humidity']}%")

        settings = get_device_settings(db)
        current_mode = settings.get("mode", "visitor")

        print(f"Current mode: {current_mode}")

        motion_detected = get_mock_motion_detection()

        if motion_detected:
            print("Mock motion detected.")
            if current_mode == "security":
                print("buzzer sound")
            send_detection(db, sensor_data, motion_detected=True)
        else:
            print("No motion detected.")

        time.sleep(LOOP_DELAY)


if __name__ == "__main__":
    main()