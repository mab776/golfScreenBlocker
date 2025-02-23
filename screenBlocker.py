"""
This script is a daemon that checks a Google Calendar for active events and
launches a Chrome browser in kiosk mode if no event is active.

TODO test cfg.dualScreen = True
TODO a lot of calendar testing

"""

import os
import sys
import time
import psutil
import subprocess
from enum import Enum
from google.oauth2 import service_account
from config import Config, load_config, printConfig
from typings_google_calendar_api.events import Event
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from typing import Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from win32 import ensureWindowOnTop

from logger import Logger
Logger("SCREEN BLOCKER", True)


SCOPES = ['https://www.googleapis.com/auth/calendar']


class MessageType(Enum):
    timesUp = "timesUp "
    backToback = "backtoback"
    boot = "boot"


# Load configuration settings for Google Calendar and Chrome
try:
    cfg: Config = load_config()
except Exception as e:
    print(f"FATAL ERROR: Error loading configuration settings: {e}")
    sys.exit(1)

printConfig(cfg)


def getCalendarService() -> Any:  # google build is impossible to type
    """
    Try to build and return the Google Calendar API service using service account credentials.
    Retries every 30 seconds if connection fails.
    """
    while True:
        try:
            # Load credentials from the JSON file
            credentials = service_account.Credentials.from_service_account_file(cfg.serviceAccountJsonPath, scopes=SCOPES)
            serviceInstance = build("calendar", "v3", credentials=credentials)
            print("Google Calendar service initialized successfully.")
            return serviceInstance
        except Exception as e:
            print(f"Error initializing Google Calendar service: {e}")
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


def getEvents() -> Tuple[Optional[Event], Optional[Event]]:
    """
    Returns a tuple: (currentEvent, nextEvent) by checking only a narrow time window.
    """
    now: datetime = datetime.now(timezone.utc)
    timeMin: datetime = now - timedelta(minutes=1)
    timeMax: datetime = now + timedelta(minutes=10)

    try:
        events: list[Event] = calendarService.events().list(
            calendarId=cfg.calendarId,
            timeMin=timeMin.isoformat(),
            timeMax=timeMax.isoformat(),
            singleEvents=True,
            orderBy="startTime"
        ).execute().get("items", [])
    except HttpError as he:
        print(f"HTTP error during Calendar API call: {he}")
        return None, None
    except Exception as e:
        print(f"Error fetching events: {e}")
        return None, None

    currentEvent: Optional[Event] = None
    nextEvent: Optional[Event] = None

    if (cfg.verbose):
        print(f"Events found in the next 10 minutes: {len(events)}")

    for event in events:
        startStr: str = event["start"].get("dateTime", event["start"].get("date"))
        endStr: str = event["end"].get("dateTime", event["end"].get("date"))
        startTime: datetime = datetime.fromisoformat(startStr)
        endTime: datetime = datetime.fromisoformat(endStr)

        if (cfg.verbose):
            print(f"Event: {event['summary']} - Start: {startTime} - End: {endTime}")

        if endTime <= now:
            continue
        else:
            if startTime <= now:
                currentEvent = event
            elif nextEvent is None:
                nextEvent = event

    return currentEvent, nextEvent


def killChrome() -> None:
    """
    Kill all Chrome processes, if any are running.
    """

    if (cfg.verbose):
        print("killChrome() called")

    alreadyLogged = False
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():
                psutil.Process(process.info["pid"]).terminate()
                if not alreadyLogged:
                    print("Chrome processes found. Terminating...")
                    alreadyLogged = True
    except Exception as e:
        print(f"Error killing Chrome processes: {e}")


def startChrome(msgType: MessageType) -> None:
    """
    Start Chrome in kiosk mode. If cfg.dualScreen is True, launch two instances
    with different window-position flags; otherwise, launch one.
    """

    if cfg.verbose:
        print("startChrome() called")

    # Do not start if Chrome is already running.
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():
                return
    except Exception as e:
        print(f"Error checking Chrome processes: {e}")

    print(f"Starting Chrome in kiosk mode. Message type: {msgType.value} | dual screen: {cfg.dualScreen}")

    # start chrome with "display.html" of this repo
    currentPath = os.path.dirname(os.path.realpath(__file__))
    url = f"file:///{currentPath}/display.html?msg={msgType.value}"

    if cfg.verbose:
        print(f"URL: {url}")

    if cfg.dualScreen:
        # Adjust the window positions to match dual-monitor configuration.
        try:
            subprocess.Popen(kioskCommand + ["--window-position=0,0", url])
            subprocess.Popen(kioskCommand + ["--window-position=1920,0", url])
        except Exception as e:
            print(f"Error starting dual-screen Chrome: {e}")
    else:
        try:
            subprocess.Popen(kioskCommand + [url])
        except Exception as e:
            print(f"Error starting Chrome: {e}")
    time.sleep(1)
    ensureWindowOnTop("Chrome", cfg.verbose)


def main() -> None:

    # fresh start
    killChrome()
    time.sleep(5)

    eventLogged = False
    while True:

        if (cfg.verbose):
            print("Main loop iteration.")

        try:
            now = datetime.now(timezone.utc)
            currentEvent, nextEvent = getEvents()

            if (cfg.verbose):
                if (currentEvent is not None):
                    print(f"Current event: {currentEvent['summary']}")
                else:
                    print("No current event")
                if (nextEvent is not None):
                    print(f"Next event: {nextEvent['summary']}")
                else:
                    print(f"Next event: {nextEvent}")

            if currentEvent is not None:

                if (cfg.verbose):
                    print("Current event exsit")

                boot = False
                if not eventLogged:
                    print(f"Event active now: {currentEvent['summary']}")
                    eventLogged = True

                # make sure Chrome is not running during an event
                killChrome()

                currentEnd = datetime.fromisoformat(
                    currentEvent["end"].get("dateTime", currentEvent["end"].get("date"))
                )

                # if current event ends within the next 20 seconds
                secondToEnd = (currentEnd - now).total_seconds()

                if (cfg.verbose):
                    hours = int(secondToEnd // 3600)
                    minutes = int(secondToEnd // 60)
                    seconds = int(secondToEnd % 60)
                    print(f"current event ends in {hours:02d}:{minutes:02d}:{seconds:02d}")

                if secondToEnd <= 30:
                    if (cfg.verbose):
                        print("Event ending soon")

                    eventLogged = False
                    # check for back-to-back events
                    if nextEvent is not None:
                        time.sleep(secondToEnd)
                        print("Back-to-back events detected. Displaying message.")
                        startChrome(msgType=MessageType.backToback)
                        time.sleep(20)  # display message for 20 seconds
                        killChrome()
                    # default message
                    else:
                        time.sleep(secondToEnd)
                        print("Event finished. Starting blocker.")
                        startChrome(msgType=MessageType.timesUp)
            else:
                if (cfg.verbose):
                    print("No current event")

                # If a future event is within 5 minutes, remove the blocker.
                if nextEvent is not None:
                    nextStart = datetime.fromisoformat(nextEvent["start"].get(
                        "dateTime", nextEvent["start"].get("date"))
                    )
                    secondsToNext = (nextStart - now).total_seconds()

                    if (cfg.verbose):
                        hours = int(secondsToNext // 3600)
                        minutes = int(secondsToNext // 60)
                        seconds = int(secondsToNext % 60)
                        print(f"Next event Starting in {hours:02d}:{minutes:02d}:{seconds:02d}")

                    if secondsToNext <= 5 * 60:
                        print(f"Next event within 5 minutes. Disabling blocker.  {nextEvent['summary']}")
                        killChrome()
                        # Wait to make sure the event will be active
                        time.sleep(secondsToNext + 10)
                        continue
                    else:

                        if (cfg.verbose):
                            print("No event active, next event is not within 5 minutes")

                        # If no event is active, make sure Chrome is running.
                        startChrome(msgType=MessageType.boot)
                else:
                    if (cfg.verbose):
                        print("No event active, no next event")

                    # If no event is active, make sure Chrome is running.
                    startChrome(msgType=MessageType.boot)

        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            ensureWindowOnTop("Chrome", cfg.verbose)
            time.sleep(20)


if __name__ == "__main__":
    main()
