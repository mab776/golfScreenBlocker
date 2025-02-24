import ctypes
import win32gui
import win32con
import win32api
import win32process
from typing import List


def listWindows() -> None:
    """
    Lists all visible windows on the system.
    """
    def enumHandler(hwnd: int, lParam: int) -> None:
        if win32gui.IsWindowVisible(hwnd):
            print(hex(hwnd), win32gui.GetWindowText(hwnd))
    win32gui.EnumWindows(enumHandler, 0)


def findWindowBySubstring(substring: str) -> List[int]:
    """
    Finds the visible windows whose title contains the given substring.

    Args:
        substring (str): The substring to search for in the window titles.

    Returns:
        List[int]: A list of window handles that match the criteria.
    """
    def enumHandler(hwnd: int, result: List[int]) -> None:
        title = win32gui.GetWindowText(hwnd)
        if substring.lower() in title.lower():
            result.append(hwnd)
    windows: List[int] = []
    win32gui.EnumWindows(enumHandler, windows)
    return windows


def forceForegroundWindow(hwnd: int, verbose: bool = False) -> None:
    """
    Forces the specified window to the foreground by attaching the input thread.

    Due to Windows restrictions on SetForegroundWindow, we attach the thread
    input of our process to that of the target window, call SetForegroundWindow,
    then detach. If SetForegroundWindow fails with error 126, we fall back to using
    BringWindowToTop and SetActiveWindow.

    Args:
        hwnd (int): The handle of the window to bring to the foreground.
        verbose (bool): If True, prints debug information.
    """
    try:
        currentThreadId = win32api.GetCurrentThreadId()
        targetThreadId, _ = win32process.GetWindowThreadProcessId(hwnd)
        if verbose:
            print(f"Current Thread ID: {currentThreadId}, Target Thread ID: {targetThreadId}")
        # Attach our input to the target window's thread using ctypes.
        ctypes.windll.user32.AttachThreadInput(currentThreadId, targetThreadId, True)
        # Ensure the window is shown normally.
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNORMAL)
        # Attempt to bring the window to the foreground.
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            if verbose:
                print(f"SetForegroundWindow failed: {e}")
                print("execute fallback BringWindowToTop and SetActiveWindow.")
            # Fallback: try bringing the window to the top and setting it active.
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetActiveWindow(hwnd)
        # Detach the input.
        ctypes.windll.user32.AttachThreadInput(currentThreadId, targetThreadId, False)
    except Exception as e:
        print(f"Error in forceForegroundWindow: {e}")


def ensureWindowOnTop(substring: str, verbose: bool = False) -> None:
    """
    Uses pywin32 to set the target window(s) always on top and brings them to the foreground.

    Args:
        substring (str): The substring to search for in the window title (e.g. "Chrome").
        verbose (bool): If True, prints debug information.
    """
    try:
        hwndList: List[int] = findWindowBySubstring(substring)
        for hwnd in hwndList:
            if hwnd:
                if verbose:
                    print(f"{substring} window found: {hwnd}")
                # Set the window as topmost without moving/resizing it.
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                                      0, 0, 0, 0,
                                      win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
                # Restore the window if minimized.
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                # Force the window to the foreground.
                forceForegroundWindow(hwnd, verbose)
            else:
                print("Chrome window not found.")
    except Exception as e:
        print(f"Unable to set Chrome on top: {e}")


if __name__ == '__main__':
    # List all visible windows.
    listWindows()
    # Find and bring Chrome windows to the foreground.
    print(f"Chrome windows found: {findWindowBySubstring('Chrome')}")
    ensureWindowOnTop("Chrome", verbose=True)
