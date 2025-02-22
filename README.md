# golfScreenBlocker
daemon that checks a Google Calendar for active events and launches a Chrome browser in kiosk mode if no event is active.

## Installation Windows
- Clone the repository
    - `git clone https://github.com/mab776/golfScreenBlocker.git`
- create a virtual environment
   - `python -m venv venv`
- activate the virtual environment
    - `source venv/bin/activate`
- install the required packages
    - `pip install -r requirements.txt`
- copy the 'screenBlockerConfig_template.cfg' file to 'screenBlockerConfig.cfg' beside the repo folder and rename the file to 'screenBlockerConfig.cfg'
    - `cp screenBlockerConfig_template.cfg ../screenBlockerConfig.cfg`
- edit the 'screenBlockerConfig.cfg' file to include the required information
    - [google]
        - key : the API key for the Google Calendar API
        - calendar_id : the ID of the calendar to check
    - [chrome] (optional)
        - path : the path to the Chrome executable
- make the script 'startScreenBlocker.bat' start at boot
    - create a shortcut to the script
    - move the shortcut to the startup folder
        - `C:\Users\<username>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`

## use case

This is for a golf simulator. The simulator is booked in 15min slots.
The screen blocker is a webpage that displays a message when the event ends or when there is no event
active in the Google Calendar. The message is displayed in a Chrome browser kiosk fullscreen mode.

## actions

- 5min before an event start, we remove the screen blocker.
- At the exact time of the event end, if there is no other event after,
  we put the screen blocker with this message (default message):
    "all good things come to an end, your time is up.
     If you would like to extend, please add time to your booking via the le birdie app.
     Thanks for playing!"
  (the message will be french and english)
- If there is another event (back-to-back booking) immediately following,
  at the exact time of the event end,
  we display the screen blocker for 20 seconds with this message (backtoback message):
    "all good things come to an end, the next booking is ready to begin.
     Have a great day!"
  (the message will be french and english)
- at boot, if no event in the next 5min, we display the screen blocker.
  with the default message.