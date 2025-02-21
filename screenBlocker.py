"""
This script is a daemon that checks a Google Calendar for active events and
launches a Chrome browser in kiosk mode if no event is active.

Scenario:

This is for a golf simulator business. The simulator is booked in 15min slots.
The screen blocker is a webpage that displays a message when the event ends or when there is no event
active in the Google Calendar. The message is displayed in a Chrome browser kiosk fullscreen mode.

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

from enum import Enum
import sys
import time
import psutil
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Tuple
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from typings_google_calendar_api.events import Event
from config import Config, load_config


class MessageType(Enum):
    TIMEUP = "timeup"
    BACK_TO_BACK = "backtoback"


# Load configuration settings for Google Calendar and Chrome
try:
    cfg: Config = load_config()
except Exception as e:
    print(f"FATAL ERROR: Error loading configuration settings: {e}")
    sys.exit(1)


def getCalendarService() -> Any:
    """Try to build and return the Google Calendar API service.
    Retries every 30 seconds if connection fails."""
    while True:
        try:
            serviceInstance = build("calendar", "v3", developerKey=cfg.apiKey)
            print("Google Calendar service initialized successfully.")
            return serviceInstance
        except Exception as e:
            print("Error initializing Google Calendar service:", e)
            print("Retrying in 30 seconds...")
            time.sleep(30)


# Google Calendar API setup using API key authentication
calendarService: Any = getCalendarService()

# Chrome kiosk mode command
kioskCommand: list[str] = [
    cfg.chromePath,
    "--kiosk",
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
    Returns a tuple: (currentEvent, lastEvent, nextEvent) by checking only a narrow time window:
    from 5 minutes ago to 5 minutes in the future.
    - currentEvent: an event active now (startTime <= now < endTime).
    - nextEvent: the next event (first event with startTime > now).
    - lastEvent: the most recent event that ended (endTime <= now).
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
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():
                print(f"Killing Chrome process: {process.info['pid']}")
                psutil.Process(process.info["pid"]).terminate()
    except Exception as e:
        print("Error killing Chrome processes:", e)


def startChrome(msgType: MessageType = MessageType.TIMEUP) -> None:
    """
    Start Chrome in kiosk mode, passing the message type as a query parameter.
    MessageType.TIMEUP indicates the long-duration message.
    MessageType.BACK_TO_BACK indicates the short (20-second) message.
    """
    # Do not start if Chrome is already running.
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():
                return
    except Exception as e:
        print("Error checking Chrome processes:", e)

    print("Starting Chrome in kiosk mode.")
    url = cfg.htmlFile + "?msg=" + msgType.value
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
                killChrome()
            else:
                if boot:
                    startChrome(msgType=MessageType.TIMEUP)
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
                    msgType = MessageType.TIMEUP
                    if lastEvent is not None and nextEvent is not None:
                        lastEnd = datetime.fromisoformat(
                            lastEvent["end"].get("dateTime", lastEvent["end"].get("date"))
                        )
                        nextStart = datetime.fromisoformat(
                            nextEvent["start"].get("dateTime", nextEvent["start"].get("date"))
                        )
                        # Back-to-back if the next event starts exactly when the last one ended.
                        if (nextStart - lastEnd).total_seconds() < 5*60:
                            msgType = MessageType.BACK_TO_BACK
                            startChrome(msgType)
                            time.sleep(20)
                            continue
                    startChrome(msgType)
        except Exception as e:
            print("Error in main loop:", e)
        finally:
            time.sleep(30)


if __name__ == "__main__":
    main()
