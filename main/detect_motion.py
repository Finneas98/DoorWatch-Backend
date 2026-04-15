from dotenv import load_dotenv
from pathlib import Path
import os
import smtplib
from datetime import datetime, timezone
import random
import time
from email.mime.text import MIMEText

import firebase_admin
from firebase_admin import credentials, firestore
from sense_hat import SenseHat
from gpiozero import MotionSensor, Buzzer

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

SERVICE_ACCOUNT_PATH = "doorwatch-1d0ff-firebase-adminsdk-fbsvc-92eec4b22c.json"
DEVICE_ID = "doorwatch-main"

EMAIL_BOT_USERNAME = os.getenv("EMAIL_BOT_USERNAME")
EMAIL_BOT_PASSWORD = os.getenv("EMAIL_BOT_PASSWORD")
YOUR_EMAIL = "fionnan98@gmail.com"

# Mock motion settings
MOCK_MODE = False
MOTION_CHANCE = 0.3   # 30% chance of motion each loop

BUZZER_GPIO_PIN = 17
PIR_GPIO_PIN = 4         # BCM numbering
LOOP_DELAY = 5        # seconds between checks
EMAIL_COOLDOWN_SECONDS = 60

sense = SenseHat()
buzzer = Buzzer(BUZZER_GPIO_PIN)
pir = MotionSensor(PIR_GPIO_PIN)

last_email_sent_at = None


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


def update_daily_summary(db, mode: str, sensor_data: dict):
    """
    Updates the daily summary document for the current day.
    """
    now = datetime.now(timezone.utc)

    # Start of current UTC day
    day_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    # Use YYYY-MM-DD as the document ID for consistency
    doc_id = day_start.strftime("daily_summary_%Y-%m-%d")

    summary_ref = (
        db.collection("devices")
        .document(DEVICE_ID)
        .collection("analytics")
        .document(doc_id)
    )

    snapshot = summary_ref.get()

    if snapshot.exists:
        existing = snapshot.to_dict()

        old_total = existing.get("totalDetections", 0)
        new_total = old_total + 1

        old_avg_temp = existing.get("averageTemperature", 0.0)
        old_avg_humidity = existing.get("averageHumidity", 0.0)

        new_avg_temp = round(
            ((old_avg_temp * old_total) + sensor_data["temperature"]) / new_total, 2
        )
        new_avg_humidity = round(
            ((old_avg_humidity * old_total) + sensor_data["humidity"]) / new_total, 2
        )

        updated_data = {
            "date": day_start,
            "totalDetections": new_total,
            "securityDetections": existing.get("securityDetections", 0) + (1 if mode == "security" else 0),
            "visitorDetections": existing.get("visitorDetections", 0) + (1 if mode == "visitor" else 0),
            "averageTemperature": new_avg_temp,
            "averageHumidity": new_avg_humidity,
        }

        summary_ref.set(updated_data)

    else:
        summary_data = {
            "date": day_start,
            "totalDetections": 1,
            "securityDetections": 1 if mode == "security" else 0,
            "visitorDetections": 1 if mode == "visitor" else 0,
            "averageTemperature": sensor_data["temperature"],
            "averageHumidity": sensor_data["humidity"],
        }

        summary_ref.set(summary_data)

    print(f"Daily summary updated for {doc_id}")


def get_mock_motion_detection() -> bool:
    """
    Simulates PIR motion detection.
    """
    if not MOCK_MODE:
        return False
    return random.random() < MOTION_CHANCE


def trigger_buzzer(duration: float = 2.0):
    """
    Activates the buzzer for a short duration.
    """
    print("Buzzer ON")
    buzzer.on()
    time.sleep(duration)
    buzzer.off()
    print("Buzzer OFF")


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
        "source": "raspberry-pi-mock-pir" if MOCK_MODE else "raspberry-pi-real-pir"
    }

    detections_ref = db.collection("devices").document(DEVICE_ID).collection("detections")
    doc_ref = detections_ref.add(detection)

    print("Detection sent successfully.")
    print(f"Document ID: {doc_ref[1].id}")
    print(detection)


def get_pir_motion_detection() -> bool:
    """
    Reads motion state from the PIR sensor.
    """
    return pir.motion_detected


def should_send_email() -> bool:
    """
    Prevents email spam by enforcing a cooldown.
    """
    global last_email_sent_at

    now = time.time()

    if last_email_sent_at is None:
        last_email_sent_at = now
        return True

    if now - last_email_sent_at >= EMAIL_COOLDOWN_SECONDS:
        last_email_sent_at = now
        return True

    return False


def main():
    db = init_firestore()
    if MOCK_MODE:
        print("DoorWatch running with mock PIR detections...")
    else:
        print("DoorWatch running with real PIR detections...")

    while True:
        sensor_data = get_sensor_readings()
        print(
            f"Current readings -> Temp: {sensor_data['temperature']}°C, "
            f"Humidity: {sensor_data['humidity']}%"
        )

        settings = get_device_settings(db)
        current_mode = settings.get("mode", "visitor")
        email_alerts_enabled = settings.get("emailAlertsEnabled", False)
        device_name = settings.get("deviceName", "DoorWatch Main Entrance")

        print(f"Current mode: {current_mode}")

        if MOCK_MODE:
            motion_detected = get_mock_motion_detection()
        else:
            motion_detected = get_pir_motion_detection()

        print(f"PIR state: {pir.motion_detected}")

        if motion_detected:
            if MOCK_MODE:
                print("Mock motion detected.")
            else:
                print("Motion detected.")

            timestamp_iso = datetime.now(timezone.utc).isoformat()
            alarm_triggered = False
            email_sent = False

            if current_mode == "security":
                trigger_buzzer(2.0)
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

            update_daily_summary(
                db=db,
                mode=current_mode,
                sensor_data=sensor_data
            )

            time.sleep(5)
        else:
            print("No motion detected.")

        time.sleep(LOOP_DELAY)


if __name__ == "__main__":
    main()