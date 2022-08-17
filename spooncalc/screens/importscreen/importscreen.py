import os
from pathlib import Path
from typing import Callable

from kivy.uix.screenmanager import Screen
from kivy.lang import Builder

Builder.load_file(os.path.join(
    Path(__file__).parent.absolute(),
    "importscreen.kv"
))


class ImportScreen(Screen):
    """
    A screen that allows users to re-import previously exported data

    Methods
    -------
    on_import_press(filename)
        Parses activities in provided csv and inserts into database
    """
    def __init__(self, import_callback: Callable, **kwargs) -> None:
        self.import_callback = import_callback
        super().__init__(**kwargs)

    def on_import_press(self, filename: str) -> None:
        """
        Import activites from a csv file into database, ignoring duplicates

        Paramters
        ---------
        filename : str
            Relative path from `EXTERNALSTORAGE` to a csv file previously
            outputted by SpoonCalculator (see `MenuWindow.export_database`)
        """
        self.import_callback(filename)
