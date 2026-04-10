import os
import smtplib
from datetime import datetime, timezone
import random
import time
from email.mime.text import MIMEText

import firebase_admin
from firebase_admin import credentials, firestore
from sense_hat import SenseHat


SERVICE_ACCOUNT_PATH = "doorwatch-1d0ff-firebase-adminsdk-fbsvc-92eec4b22c.json"
DEVICE_ID = "doorwatch-main"

EMAIL_BOT_USERNAME = os.getenv("EMAIL_BOT_USERNAME")
EMAIL_BOT_PASSWORD = os.getenv("EMAIL_BOT_PASSWORD")
YOUR_EMAIL = "fionnan98@gmail.com"

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

def send_email(subject: str, body: str) -> bool:
    """
    Sends an email using the configured email bot account.
    Returns True if successful, False otherwise.
    """
    if not EMAIL_BOT_USERNAME or not EMAIL_BOT_PASSWORD:
        print("Email bot credentials are missing.")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_BOT_USERNAME
    msg["To"] = YOUR_EMAIL

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_BOT_USERNAME, EMAIL_BOT_PASSWORD)
            server.send_message(msg)

        print("Security alert email sent successfully.")
        return True

    except Exception as error:
        print(f"Failed to send email: {error}")
        return False


def build_security_email(device_name: str, mode: str, sensor_data: dict, timestamp_iso: str) -> tuple[str, str]:
    """
    Builds the subject and body for a security alert email.
    """
    subject = f"DoorWatch Security Alert - Motion Detected at {device_name}"

    body = f"""DoorWatch Security Alert

Motion has been detected while the system is in security mode.

Device: {device_name}
Mode: {mode}
Timestamp (UTC): {timestamp_iso}

Environmental readings at time of detection:
- Temperature: {sensor_data['temperature']} °C
- Humidity: {sensor_data['humidity']} %

This is an automated alert from your DoorWatch system.
"""

    return subject, body


def get_mock_motion_detection() -> bool:
    """
    Simulates PIR motion detection.
    """
    if not MOCK_MODE:
        return False
    return random.random() < MOTION_CHANCE


def send_detection(
        db,
        sensor_data: dict,
        motion_detected: bool,
        mode: str,
        email_sent: bool,
        alarm_triggered: bool
):
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    detection = {
        "timestamp": timestamp_iso,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "mode": mode,
        "temperature": sensor_data["temperature"],
        "humidity": sensor_data["humidity"],
        "motionDetected": motion_detected,
        "imageUrl": "",
        "emailSent": email_sent,
        "alarmTriggered": alarm_triggered,
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
        print(
            f"Current readings -> Temp: {sensor_data['temperature']}°C, "
            f"Humidity: {sensor_data['humidity']}%"
        )

        settings = get_device_settings(db)
        current_mode = settings.get("mode", "visitor")
        email_alerts_enabled = settings.get("emailAlertsEnabled", False)
        security_alarm_enabled = settings.get("securityAlarmEnabled", False)
        device_name = settings.get("deviceName", "DoorWatch Main Entrance")

        print(f"Current mode: {current_mode}")

        motion_detected = get_mock_motion_detection()

        if motion_detected:
            print("Mock motion detected.")

            timestamp_iso = datetime.now(timezone.utc).isoformat()
            alarm_triggered = False
            email_sent = False

            if current_mode == "security":
                if security_alarm_enabled:
                    print("buzzer sound")
                    alarm_triggered = True

                if email_alerts_enabled:
                    subject, body = build_security_email(
                        device_name=device_name,
                        mode=current_mode,
                        sensor_data=sensor_data,
                        timestamp_iso=timestamp_iso
                    )
                    email_sent = send_email(subject, body)

            send_detection(
                db,
                sensor_data=sensor_data,
                motion_detected=True,
                mode=current_mode,
                email_sent=email_sent,
                alarm_triggered=alarm_triggered
            )
        else:
            print("No motion detected.")

        time.sleep(LOOP_DELAY)


if __name__ == "__main__":
    main()