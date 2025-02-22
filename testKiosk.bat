@echo off
REM Use %~dp0 to get the current directory (with trailing backslash)
set "CURRENT_DIR=%~dp0"
REM Replace backslashes with forward slashes for the file URL
set "FILE_URL=%CURRENT_DIR:\=/%"
REM Build the full file URL (ensure you have three slashes after file:)
set "FULL_URL=file:///%FILE_URL%display.html"

REM Set MSG to desired value: boot / backtoback / timeup / (or leave empty for default)
set "MSG=?msg=backtoback"

"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
    --kiosk ^
    --incognito ^
    --disable-infobars ^
    --noerrdialogs ^
    --disable-component-update ^
    --check-for-update-interval=31536000 ^
    --no-default-browser-check ^
    --no-first-run ^
    --disable-session-crashed-bubble ^
    --disable-pinch ^
    --disable-features=TranslateUI ^
    "%FULL_URL%%MSG%"
