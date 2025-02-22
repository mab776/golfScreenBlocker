"""
This script is a daemon that checks a Google Calendar for active events and
launches a Chrome browser in kiosk mode if no event is active.

Scenario:

This is for a golf simulator. The simulator is booked in 15min slots.
The screen blocker is a webpage that displays a message when the event ends or when there is no event
active in the Google Calendar. The message is displayed in a Chrome browser kiosk fullscreen mode.

TODO message will need to pop on dual screen

Client needs:

- 5min before an event start, we remove the screen blocker.
- At the exact time of the event end, if there is no other event after,
  we put the screen blocker with this message (default message):
    "all good things come to an end, your time is up.
     If you would like to extend, please add time to your booking via the le birdie app.
     Thanks for playing!"
  (the message will be french and english)
- If there is another event (back-to-back booking) immediately following,
  at the exact time of the event end,
  we display the screen blocker for 20 seconds with this message (backtoback message):
    "all good things come to an end, the next booking is ready to begin.
     Have a great day!"
  (the message will be french and english)
- at boot, if no event in the next 5min, we display the screen blocker.
  with the default message.
"""

import os
import sys
import time
import psutil
import subprocess
from enum import Enum
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typings_google_calendar_api.events import Event
from config import Config, load_config
from logger import Logger

# Import the service account module
from google.oauth2 import service_account

DUAL_SCREEN = False

SCOPES = ['https://www.googleapis.com/auth/calendar']


class MessageType(Enum):
    timesUp = "timesUp "
    backToback = "backtoback"
    boot = "boot"


# Initialize the logger
Logger("SCREEN BLOCKER", True)

# Load configuration settings for Google Calendar and Chrome
try:
    cfg: Config = load_config()
except Exception as e:
    print(f"FATAL ERROR: Error loading configuration settings: {e}")
    sys.exit(1)


def getCalendarService() -> Any:
    """Try to build and return the Google Calendar API service using service account credentials.
    Retries every 30 seconds if connection fails."""
    while True:
        try:
            # Load credentials from the JSON file (cfg.serviceAccountJsonPath now holds the JSON file path)
            credentials = service_account.Credentials.from_service_account_file(cfg.serviceAccountJsonPath, scopes=SCOPES)
            serviceInstance = build("calendar", "v3", credentials=credentials)
            print("Google Calendar service initialized successfully.")
            return serviceInstance
        except Exception as e:
            print("Error initializing Google Calendar service:", e)
            print("Retrying in 30 seconds...")
            time.sleep(30)


# Google Calendar API setup using service account authentication
calendarService: Any = getCalendarService()

# Chrome kiosk mode command
kioskCommand: list[str] = [
    cfg.chromePath,
    "--kiosk",
    "--incognito",
    "--disable-infobars",
    "--noerrdialogs",
    "--disable-component-update",
    "--check-for-update-interval=31536000",
    "--no-default-browser-check",
    "--no-first-run",
    "--disable-session-crashed-bubble",
    "--disable-pinch",
    "--disable-features=TranslateUI"
]


def getEvents() -> Tuple[Optional[Event], Optional[Event], Optional[Event]]:
    """
    Returns a tuple: (currentEvent, lastEvent, nextEvent) by checking only a narrow time window.
    """
    now = datetime.now(timezone.utc)
    timeMin = now - timedelta(minutes=5)
    timeMax = now + timedelta(minutes=5)
    try:
        events: list[Event] = calendarService.events().list(
            calendarId=cfg.calendarId,
            timeMin=timeMin.isoformat(),
            timeMax=timeMax.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute().get("items", [])
    except HttpError as he:
        print("HTTP error during Calendar API call:", he)
        return None, None, None
    except Exception as e:
        print("Error fetching events:", e)
        return None, None, None

    currentEvent = None
    nextEvent = None
    lastEvent = None

    for event in events:
        startStr: str = event["start"].get("dateTime", event["start"].get("date"))
        endStr: str = event["end"].get("dateTime", event["end"].get("date"))
        startTime: datetime = datetime.fromisoformat(startStr)
        endTime: datetime = datetime.fromisoformat(endStr)
        if startTime <= now < endTime:
            currentEvent = event
        elif startTime > now and nextEvent is None:
            nextEvent = event
        elif endTime <= now:
            # Pick the event that ended most recently
            if (lastEvent is None or
                    datetime.fromisoformat(lastEvent["end"].get("dateTime", lastEvent["end"].get("date"))) < endTime):
                lastEvent = event

    return currentEvent, lastEvent, nextEvent


def killChrome() -> None:
    """Kill all Chrome processes, if any are running."""
    alreadyLogged = False
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():
                psutil.Process(process.info["pid"]).terminate()
                if not alreadyLogged:
                    print("Chrome processes found. Terminating...")
                    alreadyLogged = True
    except Exception as e:
        print("Error killing Chrome processes:", e)


def startChrome(msgType: MessageType = MessageType.timesUp) -> None:
    """
    Start Chrome in kiosk mode. If DUAL_SCREEN is True, launch two instances
    with different window-position flags; otherwise, launch one.
    """
    # Do not start if Chrome is already running.
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():
                return
    except Exception as e:
        print("Error checking Chrome processes:", e)

    print(f"Starting Chrome in kiosk mode. Message type: {msgType.value}")
    # url = current path + display.html?msg= + msgType
    currentPath = os.path.dirname(os.path.realpath(__file__))
    url = f"file:///{currentPath}/display.html?msg={msgType.value}"

    if DUAL_SCREEN:
        # Adjust the window positions to match dual-monitor configuration.
        try:
            subprocess.Popen(kioskCommand + ["--window-position=0,0", url])
            subprocess.Popen(kioskCommand + ["--window-position=1920,0", url])
        except Exception as e:
            print("Error starting dual-screen Chrome:", e)
    else:
        try:
            subprocess.Popen(kioskCommand + [url])
        except Exception as e:
            print("Error starting Chrome:", e)


def main() -> None:
    boot = True
    while True:
        try:
            now = datetime.now(timezone.utc)
            currentEvent, lastEvent, nextEvent = getEvents()

            if currentEvent is not None:
                print("Event active now:", currentEvent["summary"])
                killChrome()
            else:
                if boot:
                    print("Boot sequence: no event active.")
                    startChrome(msgType=MessageType.boot)
                    boot = False
                else:
                    # If a future event is within 5 minutes, disable the blocker.
                    if nextEvent is not None:
                        nextStart = datetime.fromisoformat(
                            nextEvent["start"].get("dateTime", nextEvent["start"].get("date"))
                        )
                        secondsToNext = (nextStart - now).total_seconds()
                        if secondsToNext <= 5 * 60:
                            killChrome()
                            time.sleep(5 * 60)
                            continue  # Skip starting Chrome if a booking is imminent.

                    # Determine the appropriate message.
                    msgType = MessageType.timesUp
                    if lastEvent is not None and nextEvent is not None:
                        lastEnd = datetime.fromisoformat(
                            lastEvent["end"].get("dateTime", lastEvent["end"].get("date"))
                        )
                        nextStart = datetime.fromisoformat(
                            nextEvent["start"].get("dateTime", nextEvent["start"].get("date"))
                        )
                        # Trigger back-to-back mode if the gap is very small (e.g. <30 sec)
                        if (nextStart - lastEnd).total_seconds() < 30:
                            msgType = MessageType.backToback
                            startChrome(msgType)
                            time.sleep(20)
                            continue  # will kill the browser
                    startChrome(msgType)
        except Exception as e:
            print("Error in main loop:", e)
        finally:
            time.sleep(5)


if __name__ == "__main__":
    main()
