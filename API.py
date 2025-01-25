import sys
import os
import re

__all__ = [
    'TerminalAPI',
    'Element',
    'Window'
]

ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')

def strLen(s):
    return len(ansi_escape.sub('', s))
def ANSILen(s):
    return len(s) - len(ansi_escape.sub('', s))

class Row:
    def __init__(self, data=''):
        self.data = list(data)
    
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
        nl = []
        out = ''
        for i in s:
            if ansi_escape.sub('', i) == '':
                out += i
            else:
                nl.append(out+i)
                out = ''
        if out:
            nl.append(out)
        return nl
    
    def __add__(self, other):
        return Row(self.data+self.split(other))
    
    def __str__(self):
        return ''.join(self.data)
    def __repr__(self): return str(self)

class Screen:
    def __init__(self, API):
        self.API: TerminalAPI = API
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

class TerminalAPI:
    def __init__(self):
        self._elms = []
        self._RawMouse = [0, 0]
        self._MouseStatus = 0
        self._MouseSensitivity = [0.249, 0.13]
        self.Screen = Screen(self)
        self._oldScreen = Screen(self)
    
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
        redraw = False
        for window in self._elms:
            if window.update():
                redraw = True
        return redraw
    
    def drawAll(self):
        self._oldScreen, self.Screen = self.Screen, self._oldScreen
        self.Screen.Clear()
        for window in self._elms:
            window.draw()
    
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

class Element:
    API: TerminalAPI # API class variable will be set here, going down to all Element subclasses to use!

    def __new__(cls, *args, **kwargs):
        elm = super().__new__(cls)
        cls.API.add_elm(elm)
        return elm

    def __del__(self):
        self.API.remove_elm(self)
    
    def draw(self):
        pass

    def update(self):
        return False

    @property
    def _Screen(self) -> Screen:
        return self.API.Screen
    
    def _Write(self, x, y, *args):
        """Writes "".join(args) at (x, y)"""
        self._Screen.Write(x, y, *args)

class Border(Element):
    def draw(self):
        cols, rows = self.API.get_terminal_size()
        self._Write(0, 0, '╭', '─' * (cols-2), '╮')
        for row in range(1, rows-1):
            self._Write(0, row, '│')
            self._Write(cols-1, row, '│')
        self._Write(0, rows-1, '╰', '─' * (cols-2), '╯')  # Bottom border

class Window(Element):
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self._width = 0
        self._height = 0
        self._grabbed = None
        self._moved = False
    
    def draw(self):
        self._draw([])
    
    @property
    def width(self):
        return self._width + 2
    @property
    def height(self):
        return self._height + 2

    def _draw(self, lines):
        width, height = max(strLen(i) for i in (lines or [''])), len(lines)
        self._width = width
        self._height = height
        self._Write(self.x, self.y, '╭', '─'*width, 'X')
        for idx, ln in enumerate(lines):
            self._Write(self.x, self.y+idx+1, f'│{ln}│')
        self._Write(self.x, self.y+height+1, '╰', '─'*width, '╯')
    
    def update(self):
        if self.API.LMB:
            if self._grabbed is None:
                mpos = self.API.Mouse
                if mpos[1] == self.y and self.x <= mpos[0] < (self.x+self.width):
                    self._moved = False
                    self._grabbed = mpos
            else:
                mpos = self.API.Mouse
                if self._grabbed != mpos:
                    self._moved = True
                    diff = [self._grabbed[0]-mpos[0], self._grabbed[1]-mpos[1]]
                    self.x -= diff[0]
                    self.y -= diff[1]
                    self._grabbed = mpos
                    return True
        else:
            if not self._moved and self._grabbed is not None:
                if self._grabbed == (self.x+self.width-1, self.y):
                    self.__del__()
                    return True
            self._grabbed = None

    def __str__(self):
        return '<Window object>'
    def __repr__(self): return str(self)
