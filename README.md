# DoorWatch Backend

Backend scripts for DoorWatch, a Raspberry Pi-based visitor logging and security monitoring system.

The backend reads motion from a PIR sensor, reads temperature and humidity from a Sense HAT, writes detection records to Firebase Firestore, updates daily analytics, and can trigger a buzzer plus email alert when the device is in security mode.

## Hardware

This project is intended to run on a Raspberry Pi with:

- PIR motion sensor
- Sense HAT
- Buzzer
- Internet connection
- Firebase project with Firestore enabled

Default GPIO pins used by `main/detect_motion.py`:

| Component | GPIO pin |
| --- | ---: |
| PIR sensor | GPIO 4 |
| Buzzer | GPIO 17 |

Update `PIR_GPIO_PIN` or `BUZZER_GPIO_PIN` in `main/detect_motion.py` if your wiring is different.

## Requirements

- Python 3.11 or later
- Raspberry Pi OS for hardware use
- Firebase service account key for your Firebase project
- Gmail app password, or another SMTP-compatible email bot account, for email alerts

Python libraries used by the project:

- `firebase-admin`
- `python-dotenv`
- `sense-hat`
- `gpiozero`

## Setup

Clone the repository and enter the project folder:

```powershell
git clone <repository-url>
cd DoorWatch-Backend
```

Create a virtual environment:

```powershell
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Activate it on Raspberry Pi OS, macOS, or Linux:

```bash
source venv/bin/activate
```

Upgrade `pip`:

```bash
python -m pip install --upgrade pip
```

Install the required libraries:

```bash
pip install firebase-admin python-dotenv sense-hat gpiozero
```

Optional: save the installed dependencies to a requirements file:

```bash
pip freeze > requirements.txt
```

If a `requirements.txt` file is added later, install from it with:

```bash
pip install -r requirements.txt
```

## Environment Variables

Download the environment variables and firebase api key and place them in the projects root directory

## Changing Email Recipient

If you wish to change the recipient of the security emails, please change this line in `main/detect_motion.py`

```python
YOUR_EMAIL = "your_email@gmail.com"
```

## Running the Project

Run the main motion detection loop:

```bash
python main/detect_motion.py
```

The main script runs continuously until stopped. Press `Ctrl+C` to stop it.

## Mock Mode

`main/detect_motion.py` includes a mock motion mode for development:

```python
MOCK_MODE = False
```

Set it to `True` to simulate PIR detections without relying on the real PIR sensor:

```python
MOCK_MODE = True
```

The mock detection chance is controlled by:

```python
MOTION_CHANCE = 0.3
```

## Project Structure

```text
DoorWatch-Backend/
+-- main/
|   +-- detect_motion.py      # Main Raspberry Pi backend loop
|   +-- firestore_test.py     # Firestore test write script
|   +-- __init__.py
+-- README.md
```
