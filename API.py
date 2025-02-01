import sys
import os
import re

__all__ = [
    'TerminalAPI',
    'Container',
    'Widget',
    'PositionedWidget'
]

ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')

def strLen(s):
    return len(ansi_escape.sub('', s))
def ANSILen(s):
    return len(s) - len(ansi_escape.sub('', s))

class Row:
    def __init__(self, data=''):
        self.data = list(data)
        self.fix()
    
    def __getitem__(self, idx):
        return self.data[idx]
    
    def __setitem__(self, idx, value):
        if idx >= len(self.data):
            self.data += ['']*(idx-len(self.data)+1)
        self.data[idx] = value
    
    def __len__(self):
        return len(self.data)
    
    def __eq__(self, other):
        if isinstance(other, str):
            return ''.join(self.data) == other
        return self.data == other.data
    
    @staticmethod
    def split(s):
        tokens = re.findall(r'(?:(?:\x1B\[[0-9;]*[a-zA-Z])?[^\x1B]?)', s)
        return [i for i in tokens if i]

    def fix(self):
        self.data = self.split(''.join(self.data))
    
    def __add__(self, other):
        nr = Row(self.data+self.split(other))
        nr.fix()
        return nr
    
    def __str__(self):
        return ''.join(self.data)
    def __repr__(self): return str(self)

class Screen:
    def __init__(self):
        self.Clear()
    
    def Clear(self):
        self.screen = {}
    
    def Write(self, x, y, *args):
        """Writes "".join(args) at (x, y)"""
        t = "".join(args)
        if x < 0:
            t = t[-x:]
            x = 0
        if y in self.screen:
            if len(self.screen[y]) >= x:
                self.screen[y] = Row(self.screen[y][:x] + Row.split(t) + self.screen[y][x+strLen(t):])
            else:
                self.screen[y] += ' '*(x-len(self.screen[y])) + t
        else:
            self.screen[y] = Row(' '*x+t)
    
    def Get(self, x, y):
        """Gets the character at (x, y)"""
        if y in self.screen:
            if len(self.screen[y]) > x:
                return self.screen[y][x]
        return ' '

class Clipboard:
    @staticmethod
    def writeSelection(data):
        os.system(f'echo "{data.replace("\"", "\\\"")}" | xsel -p --display :0')
    
    @staticmethod
    def readSelection():
        return os.popen('xsel -p --display :0').read()
    
    @staticmethod
    def write(data):
        os.system(f'echo "{data.replace("\"", "\\\"")}" | xsel -b --display :0')
    
    @staticmethod
    def read():
        return os.popen('xsel -b --display :0').read()

class TerminalAPI:
    def __init__(self):
        self._elms = []
        self.fullscreen = None
        self._RawMouse = [0, 0]
        self._MouseStatus = 0
        self._MouseSensitivity = [0.249, 0.13]
        self.Screen = Screen()
        self._oldScreen = Screen()
    
    def add_elm(self, window):
        self._elms.append(window)
    
    def remove_elm(self, window):
        if window in self._elms:
            self._elms.remove(window)
    
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
        if self.fullscreen is not None:
            for elm in self._elms:
                if elm is self.fullscreen or elm.DRAW_WHILE_FULL:
                    if elm.update():
                        return True
        redraw = False
        for elm in self._elms:
            if elm.update():
                redraw = True
        return redraw
    
    def drawAll(self):
        self._oldScreen, self.Screen = self.Screen, self._oldScreen
        self.Screen.Clear()
        if self.fullscreen is not None:
            for elm in self._elms:
                if elm is self.fullscreen or elm.DRAW_WHILE_FULL:
                    elm.draw()
        else:
            for elm in self._elms:
                elm.draw()
    
    def print(self):
        winSize = self.get_terminal_size()
        for y, oldrow in self._oldScreen.screen.items():
            if y < 0 or y > winSize[1]-1:
                continue
            if y in self.Screen.screen:
                newrow = self.Screen.screen[y]
                if oldrow != newrow:
                    new = str(newrow)+' '*max(len(oldrow)-len(newrow), 0)
                    sys.stdout.write(f'\033[{y+1};1H'+new[:winSize[0]+ANSILen(new)])
            else:
                sys.stdout.write(f'\033[{y+1};1H'+' '*min(strLen(str(oldrow)), winSize[0]))
        for y, newrow in self.Screen.screen.items():
            if y < 0 or y > winSize[1]-1:
                continue
            if y not in self._oldScreen.screen or self._oldScreen.screen[y] != newrow:
                new = str(newrow)
                sys.stdout.write(f'\033[{y+1};1H'+new[:winSize[0]+ANSILen(new)])
    
    def printAll(self):
        winSize = self.get_terminal_size()
        for y in range(winSize[1]):
            if y in self.Screen.screen:
                new = str(self.Screen.screen[y])
            else:
                new = ''
            
            sys.stdout.write(f'\033[{y+1};1H\033[K'+new[:winSize[0]+ANSILen(new)])
    
    @property
    def moveToMouse(self):
        return f'\033[{round(self.Mouse[1])};{round(self.Mouse[0])}H'
    
    @staticmethod
    def get_terminal_size():
        rows, cols = os.popen('stty size', 'r').read().split()
        return int(cols), int(rows)

class Container:
    API: TerminalAPI # API class variable will be set here, going down to all Element subclasses to use!
    DRAW_WHILE_FULL = False

    def __new__(cls, *args, **kwargs):
        elm = super().__new__(cls)
        cls.API.add_elm(elm)
        return elm

    def __del__(self):
        if self.isFullscreen:
            self.unfullscreen()
        self.API.remove_elm(self)
    
    def draw(self):
        pass

    def update(self):
        return False

    def fullscreen(self):
        self.API.fullscreen = self
    
    def unfullscreen(self):
        self.API.fullscreen = None
    
    @property
    def isFullscreen(self):
        return self.API.fullscreen == self

    @property
    def _Screen(self) -> Screen:
        return self.API.Screen
    
    def _Write(self, x, y, *args):
        """Writes "".join(args) at (x, y)"""
        self._Screen.Write(x, y, *args)

class ContainerWidgets(list):
    def __init__(self, parent, startingList=None):
        self.parent = parent
        if startingList is not None:
            super().__init__([i(self.parent) for i in startingList])
        else:
            super().__init__()
    
    def append(self, elm):
        super().append(elm(self.parent))

class Widget:
    parent: Container

    def __new__(cls, *args, **kwargs):
        sup_new = super().__new__
        def new(parent):
            elm = sup_new(cls)
            elm.parent = parent
            elm.__init__(*args, **kwargs)
            if hasattr(parent, 'widgets'):
                parent.widgets.append(elm)
            return elm
        return new
    
    def __del__(self):
        self.parent.widgets.remove(self)
    
    @property
    def API(self):
        return self.parent.API
    
    def draw(self):
        pass

    def update(self):
        return False
    
    @property
    def _Screen(self) -> Screen:
        return self.parent.Screen
    
    def _Write(self, x, y, *args):
        """Writes "".join(args) at (x, y)"""
        self._Screen.Write(x, y, *args)

class PositionedWidget(Widget):
    def __init__(self, x, y):
        self.x, self.y = x, y
    
    @property
    def realPos(self):
        return self.x+self.parent.x, self.y+self.parent.y

class Border(Container):
    def draw(self):
        cols, rows = self.API.get_terminal_size()
        self._Write(0, 0, '╭', '─' * (cols-2), '╮')
        for row in range(1, rows-1):
            self._Write(0, row, '│')
            self._Write(cols-1, row, '│')
        self._Write(0, rows-1, '╰', '─' * (cols-2), '╯')
