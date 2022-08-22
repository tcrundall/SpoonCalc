from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label


class TitleBox(BoxLayout):
    """
    A simple class that serves as a header "row" in the StackedLogsLayout
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(
            size_hint=(1, None),
            size=("20dp", "30dp"),
            **kwargs,
        )
        self.orientation = "horizontal"
        # The size hints are hardcoded, but should match those of the EntryBox
        self.add_widget(Label(text="Time", size_hint=(0.2, 1)))
        self.add_widget(Label(text="Activity", size_hint=(0.45, 1)))
        self.add_widget(Label(text="Cog", size_hint=(0.1, 1)))
        self.add_widget(Label(text="Ph.", size_hint=(0.1, 1)))
        self.add_widget(Label(text="Sp.", size_hint=(0.1, 1)))
        self.add_widget(Label(text="X", size_hint=(0.05, 1)))
