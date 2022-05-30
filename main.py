from kivy.config import Config
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '800')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout


class MainWidget(BoxLayout):
    pass


class ActivityTrackerApp(App):
    pass


if __name__ == '__main__':
    ActivityTrackerApp().run()
