"""
This module loads the configuration settings for the ScreenBlocker application.
The configuration file is expected to be located one directory level above the
directory of this script. The file should be named 'screenBlockerConfig.cfg' and
should be based on the 'screenBlockerConfig_template.cfg' file.
"""

import os
from configparser import ConfigParser
from dataclasses import dataclass

CONFIG_FILE = "screenBlockerConfig.cfg"

GOOGLE_SECTION = "google"
API_KEY_TAG = "key"
CALENDAR_ID_TAG = "calendar_id"

CHROME_SECTION = "chrome"
CHROME_PATH_TAG = "path"
HTML_FILE_TAG = "html_file"


@dataclass
class Config:
    """
    A dataclass to hold configuration values.
    """
    apiKey: str = ""
    calendarId: str = ""
    chromePath: str = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    htmlFile: str = "display.html"


def load_config() -> Config:
    """
    Load configuration values from the TOML (.cfg) file located beside
    the repository folder for this project.
    """
    configPath: str = os.path.join(
        os.path.dirname(__file__), "..", CONFIG_FILE)
    configParsed: ConfigParser = ConfigParser()

    if not configParsed.read(configPath):
        raise FileNotFoundError(f"Configuration file not found at {configPath}")

    cfg: Config = Config()

    # Retrieve values from the configuration file

    # mandatory values
    if configParsed.has_option(GOOGLE_SECTION, API_KEY_TAG):
        cfg.apiKey = configParsed.get(GOOGLE_SECTION, API_KEY_TAG)
    else:
        raise ValueError("Google API key not found in configuration file.")

    if configParsed.has_option(GOOGLE_SECTION, CALENDAR_ID_TAG):
        cfg.calendarId = configParsed.get(GOOGLE_SECTION, CALENDAR_ID_TAG)
    else:
        raise ValueError("Google Calendar ID not found in configuration file.")

    # Optional values
    if configParsed.has_section(CHROME_SECTION):
        if configParsed.has_option(CHROME_SECTION, CHROME_PATH_TAG):
            cfg.chromePath = configParsed.get(CHROME_SECTION, CHROME_PATH_TAG)

        if configParsed.has_option(CHROME_SECTION, HTML_FILE_TAG):
            cfg.htmlFile = configParsed.get(CHROME_SECTION, HTML_FILE_TAG)

    return cfg


# test the module
if __name__ == "__main__":
    cfg = load_config()
    print("Google Key:", cfg.apiKey)
    print("Calendar ID:", cfg.calendarId)
    print("Chrome Path:", cfg.chromePath)
    print("HTML File:", cfg.htmlFile)
