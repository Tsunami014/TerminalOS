from API import App, Popup, StaticPos, RelativePos
import widgets as wids
import os
import importlib

__all__ = [
    'loadExternals',

    'Help',
    'Test'
]

def loadExternals():
    path = os.path.abspath(os.path.join(os.getcwd(), __file__, '../', 'external'))
    if not os.path.exists(path):
        os.mkdir(path)
    for file in os.listdir(path):
        if file.endswith('.py'):
            importlib.import_module(file[:-3], package='external')

class Help(App):
    def init_widgets(self):
        return [
            wids.Text(StaticPos(0, 0), 'HI!')
        ]

class Test(App):
    def init_widgets(self):
        return [
            wids.Text(StaticPos(0, 0), 'Hello, World!'), 
            wids.Button(StaticPos(0, 1), 'Click me!', lambda: Popup(wids.Text(StaticPos(0, 0), 'This is a popup!\nHi!'))),
            wids.TextInput(RelativePos(1, 0, len('Hello, World! '), 0), placeholder='Type here: ')
        ]
