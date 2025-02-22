@REM script to start the screen blocker

@echo off

@REM activate virtual environment
python -m venv venv
venv\Scripts\activate

@REM start the screen blocker
python screenblocker.py
