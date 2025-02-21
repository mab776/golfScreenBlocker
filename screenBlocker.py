"""
This script is a daemon that checks a Google Calendar for active events and
launches a Chrome browser in kiosk mode if no event is active.

Scenario:

This is for a golf simulator business. The simulator is booked in 15min slots.
The screen blocker is a webpage that displays a message when the event ends or when there is no event
active in the Google Calendar. The message is displayed in a Chrome browser kiosk fullscreen mode.

Clien needs :

- 5min before an event start, we remove the screen blocker
- at the exact time of the event end, if there is no other even after,
  we put the screen blocker with this message :
    "all good things come to an end, your time is up.
     If you would like to extend, please add time to your booking via the le birdie app.
     Thanks for playing!"
    (the message will be french and english)
- if there is another event (another client) after (back-to-back booking),
  at the exact time of the event end, we display the screen blocker for 10 seconds with this message :
  "all good things come to an end, the next booking is ready to begin. Have a great day!"
  (the message will be french and english)

"""

import sys
import time
import psutil
import subprocess
from datetime import datetime, timezone
from typing import Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import Config, load_config

# Load configuration settings for google calendar and chrome
try:
    cfg: Config = load_config()
except Exception as e:
    print(f"FATAL ERROR: Error loading configuration settings: {e}")
    sys.exit(1)


def getCalendarService() -> Any:
    """Try to build and return the Google Calendar API service,
    retrying every 30 seconds if the connection fails."""
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


# RENDU ICI - reste à review "isEventActive"

def isEventActive() -> bool:
    """Check if there is an active Google Calendar event.
    On failure (for example, no internet), attempt to reinitialize the API service."""

    global calendarService

    try:
        # Use timezone-aware datetime in UTC
        now: str = datetime.now(timezone.utc).isoformat()
        eventsResult: dict[str, Any] = calendarService.events().list(
            calendarId=cfg.calendarId, timeMin=now, maxResults=1,
            singleEvents=True, orderBy="startTime"
        ).execute()
        events: list[Any] = eventsResult.get("items", [])
        if not events:
            return False  # No event means Chrome should run

        event: dict[str, Any] = events[0]
        startStr: str = event["start"].get(
            "dateTime", event["start"].get("date"))
        endStr: str = event["end"].get("dateTime", event["end"].get("date"))
        startTime: datetime = datetime.fromisoformat(startStr)
        endTime: datetime = datetime.fromisoformat(endStr)
        nowDt: datetime = datetime.now(timezone.utc)
        return startTime <= nowDt <= endTime
    except HttpError as he:
        print("HTTP error during Calendar API call:", he)
        # Attempt to reinitialize the service
        calendarService = getCalendarService()
        return False
    except Exception as e:
        print("General error in isEventActive:", e)
        # Reinitialize the service on error (e.g., due to network issues)
        calendarService = getCalendarService()
        return False


def killChrome() -> None:
    """Kill all Chrome processes. if any are running."""
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():
                print(f"Event started, Killing Chrome process: {process.info['pid']}")
                psutil.Process(process.info["pid"]).terminate()
    except Exception as e:
        print("Error killing Chrome processes:", e)


def startChrome(boot: bool) -> None:
    """Start Chrome in kiosk mode. only if it is not already running."""
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():
                return
        print("Event finished, starting Chrome in kiosk mode.")
        if boot:
            subprocess.Popen(kioskCommand + [cfg.htmlFile + "?" + cfg.bootHtmlArgument])
        else:
            subprocess.Popen(kioskCommand + [cfg.htmlFile])
    except Exception as e:
        print("Error starting Chrome:", e)


def main() -> None:

    boot = True

    while True:
        try:
            if isEventActive():
                killChrome()
            else:
                startChrome(boot)
                boot = False
        except Exception as e:
            print("Error in main loop:", e)
        finally:
            # Unatended loop - pause for 30 seconds before next iteration
            time.sleep(30)


if __name__ == "__main__":
    main()
