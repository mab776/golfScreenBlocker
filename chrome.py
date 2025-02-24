
import os
import time
import subprocess
import psutil
from enum import Enum
from config import Config
from typing import Optional
from win32 import ensureWindowOnTop


class MessageType(Enum):
    timesUp = "timesUp "
    backToback = "backtoback"
    boot = "boot"


# Chrome kiosk mode command
kioskCommand: list[str] = [
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

chromeProfile1: Optional[str] = None
chromeProfile2: Optional[str] = None


def killChrome(cfg: Config) -> None:
    """
    Kill all Chrome processes, if any are running.
    """

    if (cfg.verbose):
        print("killChrome() called")

    alreadyLogged = False
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():

                if (cfg.verbose):
                    print(f"Terminating Chrome process {process.info['name']} with PID {process.info['pid']}")

                psutil.Process(process.info["pid"]).terminate()
                if not alreadyLogged:
                    print("Chrome processes found. Terminating...")
                    alreadyLogged = True
    except Exception as e:
        print(f"Error killing Chrome processes: {e}")


def startChrome(cfg: Config, msgType: MessageType) -> None:
    """
    Start Chrome in kiosk mode. If cfg.dualScreen is True, launch two instances
    with different window-position flags and reposition them programmatically;
    otherwise, launch one.
    """
    if cfg.verbose:
        print("startChrome() called")

    # Do not start if Chrome it's already running
    try:
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if "chrome" in process.info["name"].lower():
                return
    except Exception as e:
        print(f"Error checking Chrome processes: {e}")

    print(f"Starting Chrome in kiosk mode. Message type: {msgType.value} | dual screen: {cfg.dualScreen}")
    currentPath = os.path.dirname(os.path.realpath(__file__))
    url = f"file:///{currentPath}/display.html?msg={msgType.value}"
    if cfg.verbose:
        print(f"URL: {url}")

    if cfg.dualScreen:
        try:
            subprocess.Popen([cfg.chromePath] + kioskCommand +
                             ["--window-position=9999,0", f"--user-data-dir={chromeProfile1}", url])
            subprocess.Popen([cfg.chromePath] + kioskCommand +
                             ["--window-position=0,0", f"--user-data-dir={chromeProfile2}", url])
        except Exception as e:
            print(f"Error starting dual-screen Chrome: {e}")
    else:
        try:
            subprocess.Popen([cfg.chromePath] + kioskCommand + [f"--user-data-dir={chromeProfile1}", url])
        except Exception as e:
            print(f"Error starting Chrome: {e}")

    time.sleep(1)
    ensureWindowOnTop(cfg.chromeWindowName, cfg.verbose)


def createChromeUserProfiles() -> None:
    """
    Create separate user-data directories for each Chrome instance.
    """
    global chromeProfile1, chromeProfile2

    currentPath: str = os.path.dirname(os.path.realpath(__file__))
    # Create separate user-data directories for each instance.
    chromeProfile1 = os.path.join(currentPath, "..", "chromeProfile1")
    chromeProfile2 = os.path.join(currentPath, "..", "chromeProfile2")
    os.makedirs(chromeProfile1, exist_ok=True)
    os.makedirs(chromeProfile2, exist_ok=True)


if __name__ == "__main__":
    from config import loadConfig
    cfg: Config = loadConfig()
    createChromeUserProfiles()
    startChrome(cfg, MessageType.timesUp)
    time.sleep(5)
    killChrome(cfg)
    time.sleep(2)
    startChrome(cfg, MessageType.backToback)
    time.sleep(5)
    killChrome(cfg)
    time.sleep(2)
    startChrome(cfg, MessageType.boot)
    time.sleep(5)
    killChrome(cfg)
    time.sleep(2)
    print("Test completed.")
