from API import BarElm, ClickBarElm

__all__ = [
    'BarApp'
]

class BarApp(ClickBarElm):
    BarNum = 7
    def __init__(self, app):
        self.callback = app
        self.appname = f'┤{app.__qualname__}├'
    
    def _draw(self):
        return self.appname
