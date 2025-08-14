"""Spoon Calculator App for android

This script defines and runs a kivy-based application used to
track a user's energy expenditure in terms of the abstract unit
of "spoons".

This app requires the following python libraries:
- kivy
- kivy_garden
- sqlite3

This file can be executed on mac or windows, or can be
built into an APK using buildozer/python4android.
"""

from spooncalc.app import SpoonCalcApp

if __name__ == "__main__":
    SpoonCalcApp().run()
