import sys
import os

__all__ = [
    'TerminalAPI',
    'Element',
    'Window'
]

class TerminalAPI:
    def __init__(self):
        self._windows = []
        self._RawMouse = [0, 0]
        self._MouseStatus = 0
        self._MouseSensitivity = [0.249, 0.13]
    
    def add_window(self, window):
        self._windows.append(window)
    
    def remove_window(self, window):
        self._windows.remove(window)
    
    @property
    def Mouse(self):
        return (round(self._RawMouse[0]), round(self._RawMouse[1]))
    
    @property
    def LMB(self):
        return bool(self._MouseStatus & 0x01)
    @property
    def MMB(self):
        return bool(self._MouseStatus & 4)
    @property
    def RMB(self):
        return bool(self._MouseStatus & 2)
    
    def updateAll(self):
        redraw = False
        for window in self._windows:
            if window.update():
                redraw = True
        return redraw
    
    def drawAll(self):
        for window in self._windows:
            window.draw()
    
    @property
    def moveToMouse(self):
        return f'\033[{round(self.Mouse[1])};{round(self.Mouse[0])}H'
    
    @staticmethod
    def get_terminal_size():
        rows, cols = os.popen('stty size', 'r').read().split()
        return int(rows), int(cols)

class Element:
    API: TerminalAPI # API class variable will be set here, going down to all Element subclasses to use!

class Window(Element):
    def __new__(cls, *args, **kwargs):
        window = super().__new__(cls)
        cls.API.add_window(window)
        return window
    
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self._width = 0
        self._height = 0
        self._grabbed = None
    
    def __del__(self):
        self.API.remove_window(self)
    
    def draw(self):
        self._draw([])
    
    @property
    def width(self):
        return self._width + 2
    @property
    def height(self):
        return self._height + 2

    def _draw(self, lines):
        width, height = max(len(i) for i in (lines or [''])), len(lines)
        self._width = width
        self._height = height
        sys.stdout.write(f'\033[{self.y};{self.x}H╭'+('─'*width)+'╮')
        for idx, ln in enumerate(lines):
            sys.stdout.write(f'\033[{self.y+idx+1};{self.x}H│{ln}│')
        sys.stdout.write(f'\033[{self.y+height+1};{self.x}H╰'+('─'*width)+'╯')
    
    def update(self):
        if self.API.LMB:
            if self._grabbed is None:
                mpos = self.API.Mouse
                if mpos[1] == self.y and self.x <= mpos[0] < (self.x+self.width):
                    self._grabbed = mpos
            else:
                mpos = self.API.Mouse
                if self._grabbed != mpos:
                    sys.stdout.write(''.join(f'\033[{self.y+i};{self.x}H'+' '*self.width for i in range(self.height)))
                    diff = [self._grabbed[0]-mpos[0], self._grabbed[1]-mpos[1]]
                    self.x -= diff[0]
                    self.y -= diff[1]
                    self._grabbed = mpos
        else:
            self._grabbed = None

    def __str__(self):
        return '<Window object>'
    def __repr__(self): return str(self)
