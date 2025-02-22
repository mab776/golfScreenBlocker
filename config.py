"""
This module loads the configuration settings for the ScreenBlocker application.
The configuration file is expected to be located beside this repository folder.
The file should be named 'screenBlockerConfig.cfg' and
should be based on the 'screenBlockerConfig_template.cfg' file.
location: "../screenBlockerConfig.cfg"
"""

import os
from configparser import ConfigParser
from dataclasses import dataclass
from logger import Logger
Logger("SCREEN BLOCKER", True)

CONFIG_FILE_NAME = "screenBlockerConfig.cfg"

# configuration file [google] section and tags
GOOGLE_SECTION = "google"
SERVICE_ACCOUNT_KEY = "serviceAccountJsonPath"
CALENDAR_ID_TAG = "calendar_id"

# configuration file [chrome] section and tags
CHROME_SECTION = "chrome"
CHROME_PATH_TAG = "path"


@dataclass
class Config:
    """
    A dataclass to hold configuration values.
    """
    serviceAccountJsonPath: str = ""
    calendarId: str = ""
    chromePath: str = "C:/Program Files/Google/Chrome/Application/chrome.exe"


def load_config() -> Config:
    """
    Load configuration values from the TOML (.cfg) file located beside
    the repository folder for this project.
    """
    configPath: str = os.path.join(os.path.dirname(__file__), "..", CONFIG_FILE_NAME)
    configParsed: ConfigParser = ConfigParser()

    if not configParsed.read(configPath):
        raise FileNotFoundError(f"Configuration file not found at {configPath}")

    cfg: Config = Config()

    # Retrieve values from the configuration file

    # mandatory values
    if configParsed.has_option(GOOGLE_SECTION, SERVICE_ACCOUNT_KEY):
        cfg.serviceAccountJsonPath = configParsed.get(GOOGLE_SECTION, SERVICE_ACCOUNT_KEY)
    else:
        raise ValueError("Google service account key (json path) not found in configuration file.")

    if configParsed.has_option(GOOGLE_SECTION, CALENDAR_ID_TAG):
        cfg.calendarId = configParsed.get(GOOGLE_SECTION, CALENDAR_ID_TAG)
    else:
        raise ValueError("Google Calendar ID not found in configuration file.")

    # Optional values for the Chrome path
    if configParsed.has_section(CHROME_SECTION):
        if configParsed.has_option(CHROME_SECTION, CHROME_PATH_TAG):
            cfg.chromePath = configParsed.get(CHROME_SECTION, CHROME_PATH_TAG)

    return cfg


# test the module
if __name__ == "__main__":
    cfg = load_config()
    print(f"Google Key:  {cfg.serviceAccountJsonPath}")
    print(f"Calendar ID: {cfg.calendarId}")
    print(f"Chrome Path: {cfg.chromePath}")
    print()
    print("Configuration loaded successfully.")
    print()
