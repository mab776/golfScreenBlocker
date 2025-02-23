import win32gui
import win32con
from typing import List, Tuple


def listWindows() -> None:
    """
    Enumerates all visible windows and prints their handles and titles.
    """
    def enumHandler(hwnd: int, result: List[Tuple[int, str]]) -> None:
        if win32gui.IsWindowVisible(hwnd):
            windowText = win32gui.GetWindowText(hwnd)
            if windowText:
                result.append((hwnd, windowText))
    windows: List[Tuple[int, str]] = []
    win32gui.EnumWindows(enumHandler, windows)
    for hwnd, title in windows:
        print(f"HWND: {hwnd} - Title: {title}")


def findWindowBySubstring(substring: str) -> int:
    """
    Finds the first visible window whose title contains the given substring.
    Returns The handle (HWND) of the first matching window, or 0 if not found.
    """
    matchedHwnd: int = 0

    def enumHandler(hwnd: int, result: List[int]) -> None:
        title = win32gui.GetWindowText(hwnd)
        if substring.lower() in title.lower():
            result.append(hwnd)
    windows: List[int] = []
    win32gui.EnumWindows(enumHandler, windows)
    if windows:
        matchedHwnd = windows[0]
    return matchedHwnd


def ensureWindowOnTop(substring: str, verbose: bool = False) -> None:
    """
    Use pywin32 to set the Chrome window always on top.
    Adjust the title filter as needed.
    """
    try:
        hwnd = findWindowBySubstring(substring)
        if hwnd:
            if verbose:
                print(f"{substring} window found: {hwnd}")
            # Set the window as topmost without moving/resizing it.
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                                  0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            # Restore the window if it is minimized.
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            # Bring it to the foreground.
            win32gui.SetForegroundWindow(hwnd)
        else:
            print("Chrome window not found.")
    except Exception as e:
        print(f"Unable to set Chrome on top: {e}")


if __name__ == '__main__':
    listWindows()
    print(f"Chrome window found : {findWindowBySubstring('Chrome')}")
