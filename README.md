# golfScreenBlocker
daemon that checks a Google Calendar for active events and launches a Chrome browser in kiosk mode if no event is active to lock the screen. The daemon will remove the screen-lock 5 minutes before an event starts and will lock the screen again when the event ends.

## Installation Windows
- Clone the repository
    - `git clone https://github.com/mab776/golfScreenBlocker.git`
- create a virtual environment
   - `python -m venv venv`
- activate the virtual environment
    - `venv\Scripts\activate`
- install the required packages
    - `pip install -r requirements.txt`
- copy the 'screenBlockerConfig_template.cfg' file to 'screenBlockerConfig.cfg' beside the repo folder and rename the file to 'screenBlockerConfig.cfg'
    - `cp screenBlockerConfig_template.cfg ../screenBlockerConfig.cfg`
- edit the 'screenBlockerConfig.cfg' file to include the required information
    - [google]
        - serviceAccountJsonPath : the service account key file path (JSON)
        - calendar_id : the ID of the calendar to check
    - [chrome] (optional)
        - path : the path to the Chrome executable
- make the script 'startScreenBlocker.bat' start at boot
    - create a shortcut to the script
    - move the shortcut to the startup folder
        - `C:\Users\<username>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`

## Create a Google Service Account
- Go to the Google Cloud Console
- Create a new project
- Enable the Google Calendar API
- Create a new service account
- Create a key for the service account (JSON)
- Download the service account key as a JSON file
- Copy the key beside the 'golfScreenBlocker' folder and copy it's full path to the 'screenBlockerConfig.cfg' file under the [google] section as the value for the serviceAccountJsonPath.
- Share your calendar to the service account email with 'See details of events' permission

## Find calendar ID
You can find your calendar ID in the Google Calendar web interface by following these steps:

- Open Google Calendar in a web browser.
- On the left sidebar under "My calendars", hover over the calendar you want to use and click the three dots that appear.
- Choose "Settings and sharing."
- Scroll down to the "Integrate calendar" section.
- You will see the "Calendar ID" there (it’s often an email-like address).
- Copy the calendar ID and paste it into the 'screenBlockerConfig.cfg' file, under the [google] section as the value for the calendar_id.

## Use case

This is for a golf simulator. The simulator is booked in 15min+ slots.
The screen blocker is a webpage that displays a message when the event ends or when there is no event active in the Google Calendar. The message is displayed in a Chrome browser in kiosk mode.

## Actions

- 5min before an event start, we remove the screen blocker.
- At the exact time of the event end, if there is no other event after,
  we put the screen blocker with this message (default message):
    "all good things come to an end, your time is up.
     If you would like to extend, please add time to your booking via the le birdie app.
     Thanks for playing!"
  (the message will be french and english)
- after 20sec of the default message, the message fade-out and a padlock is displayed.
  The padlock will bounce around to save the projector lamp.
- If there is another event (back-to-back booking) immediately following,
  at the exact time of the event end,
  we display the screen blocker for 20 seconds with this message (backtoback message):
    "all good things come to an end, the next booking is ready to begin.
     Have a great day!"
  (the message will be french and english)
- at boot, if no event in the next 5min, we display the screen blocker.
  with the default message.
