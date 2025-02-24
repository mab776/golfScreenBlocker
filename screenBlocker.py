"""
This script is a daemon that checks a Google Calendar for active events and
launches a Chrome browser in kiosk mode if no event is active.
"""

import sys
import time
from typing import Any
from datetime import datetime, timezone
from win32 import ensureWindowOnTop
from config import Config, loadConfig, printConfig
from googleCalendar import getCalendarService, getEvents
from chrome import MessageType, createChromeUserProfiles, killChrome, startChrome

from logger import Logger
Logger("SCREEN BLOCKER", True)

# Load configuration settings for Google Calendar and Chrome
try:
    cfg: Config = loadConfig()
except Exception as e:
    print(f"FATAL ERROR: Error loading configuration settings: {e}")
    sys.exit(1)

printConfig(cfg)

# Google Calendar API setup using service account authentication
calendarService: Any = getCalendarService(cfg)


def main() -> None:

    # fresh start
    killChrome(cfg)
    createChromeUserProfiles()
    time.sleep(5)

    eventLogged = False
    while True:

        if (cfg.verbose):
            print("Main loop iteration.")

        try:
            now = datetime.now(timezone.utc)  # events are in UTC
            currentEvent, nextEvent = getEvents(cfg, calendarService)

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
                    print("Current event exists")

                boot = False
                if not eventLogged:
                    print(f"Event active now: {currentEvent['summary']}")
                    eventLogged = True

                # make sure Chrome is not running during an event
                killChrome(cfg)

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
                        startChrome(cfg, msgType=MessageType.backToback)
                        time.sleep(20)  # display message for 20 seconds
                        killChrome(cfg)
                    # default message
                    else:
                        time.sleep(secondToEnd)
                        print("Event finished. Starting blocker.")
                        startChrome(cfg, msgType=MessageType.timesUp)
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
                        killChrome(cfg)
                        # Wait to make sure the event will be active
                        time.sleep(secondsToNext + 10)
                        continue
                    else:

                        if (cfg.verbose):
                            print("No event active, next event is not within 5 minutes")

                        # If no event is active, make sure Chrome is running.
                        startChrome(cfg, msgType=MessageType.boot)
                else:
                    if (cfg.verbose):
                        print("No event active, no next event")

                    # If no event is active, make sure Chrome is running.
                    startChrome(cfg, msgType=MessageType.boot)

        except Exception as e:
            print(f"Error in main loop: {e}")
        finally:
            ensureWindowOnTop("Chrome", cfg.verbose)
            time.sleep(20)


if __name__ == "__main__":
    main()
