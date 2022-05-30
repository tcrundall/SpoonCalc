from kivy.config import Config
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '800')

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout


class MainWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ActivityTrackerApp(App):
    pass


if __name__ == '__main__':
    ActivityTrackerApp().run()
