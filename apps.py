from API import App, Popup
import widgets as wids

__all__ = [
    'Help',
    'Test'
]

class Help(App):
    def init_widgets(self):
        return [
            wids.Text(0, 0, 'HI!')
        ]

class Test(App):
    def init_widgets(self):
        return [
            wids.Text(0, 0, 'Hello, World!'), 
            wids.Button(0, 1, 'Click me!', lambda: Popup(wids.Text(0, 0, 'This is a popup!\nHi!'))),
            wids.TextInput(len('Hello, World! '), 0, placeholder='Type here: ')
        ]
