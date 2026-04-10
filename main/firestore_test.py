from datetime import datetime, timezone
import firebase_admin
from firebase_admin import credentials, firestore
from sense_hat import SenseHat


SERVICE_ACCOUNT_PATH = "doorwatch-1d0ff-firebase-adminsdk-fbsvc-92eec4b22c.json"
DEVICE_ID = "doorwatch-main"

sense = SenseHat()

def init_firestore():
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

def send_dummy_detection(db):
    detection = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "createdAt": firestore.SERVER_TIMESTAMP,
        "mode": "visitor",
        "temperature": 21.7,
        "humidity": 48.3,
        "motionDetected": True,
        "imageUrl": "",
        "emailSent": False,
        "alarmTriggered": False,
        "source": "raspberry-pi-test"
    }

    detections_ref = db.collection("devices").document(DEVICE_ID).collection("detections")
    doc_ref = detections_ref.add(detection)

    print("Dummy detection sent successfully.")
    print(f"Document ID: {doc_ref[1].id}")

def main():
    db = init_firestore()
    send_dummy_detection(db)

if __name__ == "__main__":
    main()