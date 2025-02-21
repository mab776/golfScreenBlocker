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
  we put the screen blocker with this message (long duration message):
    "all good things come to an end, your time is up.
     If you would like to extend, please add time to your booking via the le birdie app.
     Thanks for playing!"
  (the message will be french and english)
- If there is another event (back-to-back booking) immediately following,
  at the exact time of the event end,
  we display the screen blocker for 10 seconds with this message (short duration message):
    "all good things come to an end, the next booking is ready to begin.
     Have a great day!"
  (the message will be french and english)
- at boot, if no event in the next 5min, we display the screen blocker.
  with the default (long duration message)

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


def getCalendarService() -> Resource:
    """Try to build and return the Google Calendar API service.
    Retries every 30 seconds if connection fails."""
    while True:
        try:
            serviceInstance: Resource = build("calendar", "v3", developerKey=cfg.apiKey)
            print("Google Calendar service initialized successfully.")
            return serviceInstance
        except Exception as e:
            print("Error initializing Google Calendar service:", e)
            print("Retrying in 30 seconds...")
            time.sleep(30)


# Google Calendar API setup using API key authentication
calendarService: Resource = getCalendarService()

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


def get_events() -> Tuple[Optional[dict], Optional[dict], Optional[dict]]:
    """
    Returns a tuple: (current_event, last_event, next_event) by checking only a narrow time window:
    from 5 minutes ago to 5 minutes in the future.
    - current_event: an event active now (startTime <= now < endTime).
    - next_event: the next event (first event with startTime > now).
    - last_event: the most recent event that ended (endTime <= now).
    """
    now = datetime.now(timezone.utc)
    time_min = now - timedelta(minutes=5)
    time_max = now + timedelta(minutes=5)

    try:
        eventsResult: dict[str, Any] = calendarService.events().list(
            calendarId=cfg.calendarId,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute()
    except HttpError as he:
        print("HTTP error during Calendar API call:", he)
        return None, None, None
    except Exception as e:
        print("Error fetching events:", e)
        return None, None, None

    events: list[Any] = eventsResult.get("items", [])
    current_event = None
    next_event = None
    last_event = None

    for event in events:
        startStr: str = event["start"].get("dateTime", event["start"].get("date"))
        endStr: str = event["end"].get("dateTime", event["end"].get("date"))
        startTime: datetime = datetime.fromisoformat(startStr)
        endTime: datetime = datetime.fromisoformat(endStr)
        if startTime <= now < endTime:
            current_event = event
        elif startTime > now and next_event is None:
            next_event = event
        elif endTime <= now:
            # Pick the event that ended most recently
            if (last_event is None or
                    datetime.fromisoformat(last_event["end"].get("dateTime", last_event["end"].get("date"))) < endTime):
                last_event = event

    return current_event, last_event, next_event


def killChrome() -> None:
    """Kill all Chrome processes, if any are running."""
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():
                print(f"Killing Chrome process: {process.info['pid']}")
                psutil.Process(process.info["pid"]).terminate()
    except Exception as e:
        print("Error killing Chrome processes:", e)


def startChrome(msgtype: MessageType = MessageType.TIMEUP) -> None:
    """
    Start Chrome in kiosk mode, passing the message type as a query parameter.
    MessageType.TIMEUP indicates the long-duration message.
    MessageType.BACK_TO_BACK indicates the short (10-second) message.
    """
    # Do not start if Chrome is already running.
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():
                return
    except Exception as e:
        print("Error checking Chrome processes:", e)

    print("Starting Chrome in kiosk mode.")
    url = cfg.htmlFile + "?msg=" + msgtype.value
    try:
        subprocess.Popen(kioskCommand + [url])
    except Exception as e:
        print("Error starting Chrome:", e)


def main() -> None:
    boot = True
    while True:
        try:
            now = datetime.now(timezone.utc)
            current_event, last_event, next_event = get_events()

            if current_event is not None:
                killChrome()
            else:
                if boot:
                    startChrome(msgtype=MessageType.TIMEUP)
                    boot = False
                else:
                    # If a future event is within 5 minutes, disable the blocker.
                    if next_event is not None:
                        next_start = datetime.fromisoformat(
                            next_event["start"].get("dateTime", next_event["start"].get("date"))
                        )
                        seconds_to_next = (next_start - now).total_seconds()
                        if seconds_to_next <= 5 * 60:
                            killChrome()
                            time.sleep(5 * 60)
                            continue  # Skip starting Chrome if a booking is imminent.

                    # Determine the appropriate message.
                    msgtype = MessageType.TIMEUP
                    if last_event is not None and next_event is not None:
                        last_end = datetime.fromisoformat(
                            last_event["end"].get("dateTime", last_event["end"].get("date"))
                        )
                        next_start = datetime.fromisoformat(
                            next_event["start"].get("dateTime", next_event["start"].get("date"))
                        )
                        # Back-to-back if the next event starts exactly when the last one ended.
                        if (next_start - last_end).total_seconds() == 0:
                            msgtype = MessageType.BACK_TO_BACK
                    startChrome(msgtype)

        except Exception as e:
            print("Error in main loop:", e)
        finally:
            time.sleep(30)


if __name__ == "__main__":
    main()
