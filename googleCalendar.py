
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typings_google_calendar_api.events import Event
from typing import Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from config import Config

SCOPES = ['https://www.googleapis.com/auth/calendar']


def getCalendarService(cfg: Config) -> Any:  # google build is impossible to type
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


def getEvents(cfg: Config, calendarService: Any) -> Tuple[Optional[Event], Optional[Event]]:
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


# test module
if __name__ == "__main__":
    from config import loadConfig
    cfg = loadConfig()
    calendarService = getCalendarService(cfg)
    currentEvent, nextEvent = getEvents(cfg, calendarService)
    print(f"Current Event: {currentEvent}")
    print(f"Next Event: {nextEvent}")
    print()
    print("Google Calendar API functions test finished.")
    print()
