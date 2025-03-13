from enum import Enum
import math
import re
import sys
import time
import shutil

__all__ = [
    'TerminalAPI',

    'Position',
        'StaticPos',
        'RelativePos',
    'Container',
        'Window',
            'FullscreenWindow',
        'Popup',
    'Widget',
        'PositionedWidget',
    'App',
        'FullscreenApp',
]

ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')

def strLen(s):
    return len(ansi_escape.sub('', s))
def ANSILen(s):
    return len(s) - len(ansi_escape.sub('', s))
def split(s):
    return re.findall(r'(?:\x1B\[[0-9;]*[a-zA-Z])|[^\x1B]', s)

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
        tokens = re.findall(r'(?:(?:\x1B\[[0-9;]*[a-zA-Z])*[^\x1B]?)', s)
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
                self.screen[y] += ' '*(x-strLen(str(self.screen[y]))) + t
        else:
            self.screen[y] = Row(' '*x+t)
    
    def Get(self, x, y):
        """Gets the character at (x, y)"""
        if y in self.screen:
            if len(self.screen[y]) > x:
                return self.screen[y][x]
        return ' '

class Clipboard:
    CLIP = []
    MAX_LEN = 25
    
    @classmethod
    def write(cls, data):
        cls.CLIP.append(data)
        if len(cls.CLIP) > cls.MAX_LEN:
            cls.CLIP = cls.CLIP[len(cls.CLIP)-cls.MAX_LEN:]
    
    @classmethod
    def read(cls):
        return cls.CLIP[-1]

class ScreenModes(Enum):
    APPS = 0
    """The app view"""
    LAYOUT = 1
    """The layout editor view"""
    CHOOSE = 2
    """The choose an app view"""

class TerminalAPI:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.events = []
        self.fullscreen = None
        self.windows = []
        self.focus = [0, 0]
        self.layout = [[[], None]]
        self.grid = [[None]]
        self.selected = None
        self.searching = ''
        self.mode = ScreenModes.LAYOUT
        self.Screen = Screen()
        self._oldScreen = Screen()
    
    def updateAll(self):
        if self.mode == ScreenModes.APPS:
            if self.fullscreen is not None:
                redraw = self.fullscreen.update()
                for elm in self.windows:
                    if elm.DRAW_WHILE_FULL:
                        if elm.update():
                            redraw = True
                return redraw
            redraw = False
            for elm in self.windows:
                if elm.update():
                    redraw = True
            return redraw
        elif self.mode == ScreenModes.LAYOUT:
            sze = self.get_terminal_size()
            changed = False
            for ev in self.events:
                changed_now = False
                if ev.state == 1:
                    # Creation - ctrl+<>
                    if ev == 'ctrl+W':
                        hei = (self.layout[self.focus[1]][1] or sze[1]-sum([i[1] for i in self.layout if i[1]]+[0]))/2
                        if hei >= 2:
                            self.grid.insert(self.focus[1], [None])
                            self.layout.insert(self.focus[1], [[], math.floor(hei)])
                            if self.focus[1]+1 < len(self.layout)-1:
                                self.layout[self.focus[1]+1][1] = math.ceil(hei)
                        changed_now = True
                    elif ev == 'ctrl+S':
                        hei = (self.layout[self.focus[1]][1] or sze[1]-sum([i[1] for i in self.layout if i[1]]+[0]))/2
                        if hei >= 2:
                            self.grid.insert(self.focus[1], [None])
                            self.layout.insert(self.focus[1], [[], math.ceil(hei)])
                            self.focus[1] += 1
                            if self.focus[1] < len(self.layout)-1:
                                self.layout[self.focus[1]][1] = math.floor(hei)
                            changed_now = True
                    elif ev == 'ctrl+A':
                        if self.focus[0] == len(self.layout[self.focus[1]][0]):
                            wid = (sze[0]-sum(self.layout[self.focus[1]][0]+[0]))/2
                        else:
                            wid = self.layout[self.focus[1]][0][self.focus[0]]/2
                            if wid >= 6:
                                self.layout[self.focus[1]][0][self.focus[0]] = math.floor(wid)
                        if wid >= 6:
                            self.grid[self.focus[1]].insert(self.focus[0], None)
                            self.layout[self.focus[1]][0].insert(self.focus[0], math.ceil(wid))
                            changed_now = True
                    elif ev == 'ctrl+D':
                        if self.focus[0] == len(self.layout[self.focus[1]][0]):
                            wid = (sze[0]-sum(self.layout[self.focus[1]][0]+[0]))/2
                        else:
                            wid = self.layout[self.focus[1]][0][self.focus[0]]/2
                            if wid >= 2:
                                self.layout[self.focus[1]][0][self.focus[0]] = math.ceil(wid)
                        if wid >= 2:
                            self.grid[self.focus[1]].insert(self.focus[0], None)
                            self.layout[self.focus[1]][0].insert(self.focus[0], math.floor(wid))
                            self.focus[0] += 1
                            changed_now = True
                    
                    # Deletion - ctrl+alt+<>
                    elif ev == 'ctrl+alt+W':
                        if self.focus[1] != 0:
                            self.focus[1] -= 1
                            self.grid.pop(self.focus[1])
                            _, eh = self.layout.pop(self.focus[1])
                            if self.layout[self.focus[1]][1]:
                                self.layout[self.focus[1]][1] += eh
                            changed_now = True
                    elif ev == 'ctrl+alt+S':
                        if self.focus[1] < len(self.layout)-1:
                            self.grid.pop(self.focus[1])
                            _, eh = self.layout.pop(self.focus[1]+1)
                            self.layout[self.focus[1]][1] += eh
                            changed_now = True
                    elif ev == 'ctrl+alt+A':
                        if self.focus[0] > 0:
                            self.focus[0] -= 1
                            self.grid[self.focus[1]].pop(self.focus[0])
                            ew = self.layout[self.focus[1]][0].pop(self.focus[0])
                            if self.focus[0] < len(self.layout[self.focus[1]][0]):
                                self.layout[self.focus[1]][0][self.focus[0]] += ew
                            changed_now = True
                    elif ev == 'ctrl+alt+D':
                        if self.focus[0] == len(self.layout[self.focus[1]][0])-1:
                            self.grid[self.focus[1]].pop(-1)
                            self.layout[self.focus[1]][0].pop(-1)
                        elif self.focus[0] < len(self.layout[self.focus[1]][0])-1:
                            self.grid[self.focus[1]].pop(self.focus[0]+1)
                            ew = self.layout[self.focus[1]][0].pop(self.focus[0]+1)
                            self.layout[self.focus[1]][0][self.focus[0]] += ew
                        changed_now = True
                    
                    elif ev == 'H': # Testing
                        self.grid[self.focus[1]][self.focus[0]] = 'HELLO\nworld'
                        changed_now = True
                    elif ev == 'B': # Testing
                        self.grid[self.focus[1]][self.focus[0]] = 'BYE\nbyeeee'
                        changed_now = True

                    # Arrow keys switch between
                    elif ev == 'UP':
                        self.focus[1] -= 1
                        changed_now = True
                    elif ev == 'DOWN':
                        self.focus[1] += 1
                        changed_now = True
                    elif ev == 'LEFT':
                        self.focus[0] -= 1
                        changed_now = True
                    elif ev == 'RIGHT':
                        self.focus[0] += 1
                        changed_now = True
                    
                    elif ev == 'SPACE' or (ev == 'ENTER' and self.selected is not None):
                        if self.selected is not None:
                            self.grid[self.focus[1]][self.focus[0]] = self.selected
                            self.selected = None
                        else:
                            self.selected = self.grid[self.focus[1]][self.focus[0]]
                            self.grid[self.focus[1]][self.focus[0]] = None
                        changed = True
                    elif ev in ('BACKSPACE', 'DELETE'):
                        self.grid[self.focus[1]][self.focus[0]] = None
                        changed = True
                    elif ev == 'ENTER':
                        self.mode = ScreenModes.CHOOSE
                        self.searching = ''
                        changed = True
                
                # Just letters resize
                elif ev == 'W' and ev.heldFor % 2 == 0:
                    if self.focus[1] < len(self.layout)-1:
                        if self.layout[self.focus[1]][1] > 3:
                            self.layout[self.focus[1]][1] -= 1
                            changed_now = True
                    elif self.focus[1] > 0:
                        h = sze[1]-sum(i[1] for i in self.layout if i[1])
                        if h > 3:
                            self.layout[self.focus[1]-1][1] += 1
                        changed_now = True
                elif ev == 'S' and ev.heldFor % 2 == 0:
                    if self.focus[1] < len(self.layout)-1:
                        if sum(i[1] for i in self.layout if i[1])+1<(sze[1]-3):
                            self.layout[self.focus[1]][1] += 1
                            changed_now = True
                    elif self.focus[1] > 0 and self.layout[self.focus[1]-1][1] > 3:
                        self.layout[self.focus[1]-1][1] -= 1
                        changed_now = True
                elif ev == 'A':
                    if self.focus[0] < len(self.layout[self.focus[1]][0]) and self.layout[self.focus[1]][0][self.focus[0]] > 3:
                        self.layout[self.focus[1]][0][self.focus[0]] -= 1
                        changed_now = True
                    elif self.focus[0] > 0:
                        w = sze[0]-sum(self.layout[self.focus[1]][0])
                        if w > 3:
                            self.layout[self.focus[1]][0][self.focus[0]-1] += 1
                            changed_now = True
                elif ev == 'D':
                    if self.focus[0] < len(self.layout[self.focus[1]][0]):
                        if sum(self.layout[self.focus[1]][0])+1<(sze[0]-3):
                            self.layout[self.focus[1]][0][self.focus[0]] += 1
                            changed_now = True
                    elif self.focus[0] > 0 and self.layout[self.focus[1]][0][self.focus[0]-1] > 3:
                        self.layout[self.focus[1]][0][self.focus[0]-1] -= 1
                        changed_now = True
                
                if changed_now:
                    if self.focus[1] < 0:
                        self.focus[1] = 0
                    elif self.focus[1] >= len(self.layout):
                        self.focus[1] = len(self.layout)-1
                    
                    if self.focus[0] < 0:
                        self.focus[0] = 0
                    elif self.focus[0] > len(self.layout[self.focus[1]][0]):
                        self.focus[0] = len(self.layout[self.focus[1]][0])
                
                changed = changed or changed_now
            return changed
        elif self.mode == ScreenModes.CHOOSE:
            changed = False
            for ev in self.events:
                if ev.state == 1:
                    if ev == 'ESC':
                        self.mode = ScreenModes.LAYOUT
                        changed = True
                    elif ev.unicode is not None:
                        self.searching += ev.unicode
                        changed = True
            return changed
        return False

    def resetScreens(self):
        self._oldScreen, self.Screen = self.Screen, self._oldScreen
        self.Screen.Clear()
    
    def drawAll(self):
        if self.mode == ScreenModes.APPS:
            if self.fullscreen is not None:
                self.fullscreen.draw()
                for elm in self.windows:
                    if elm.DRAW_WHILE_FULL:
                        elm.draw()
            else:
                for elm in self.windows:
                    elm.draw()
        elif self.mode == ScreenModes.CHOOSE:
            sze = self.get_terminal_size()
            txt = self.searching
            lines = txt.split('\n')
            midy = (sze[1]-len(lines)+1)//2
            for idx, ln in enumerate(lines):
                self.Screen.Write((sze[0]-len(ln))//2, midy+idx, ln)
    
    def _print_borders(self):
        sze = self.get_terminal_size()
        self.Screen.Write(0, 0, '┌', '─' * (sze[0]-2), '┐')
        for row in range(1, sze[1]-1):
            self.Screen.Write(0, row, '│')
            self.Screen.Write(sze[0]-1, row, '│')
        self.Screen.Write(0, sze[1]-1, '└', '─' * (sze[0]-2), '┘')
        if self.mode == ScreenModes.CHOOSE:
            return
        sy = 0
        for yidx, (row, h) in enumerate(self.layout):
            if h is None:
                h = sze[1]-sy-1
            else:
                for ix in range(1, sze[0]-1):
                    self.Screen.Write(ix, sy+h, '─')
                self.Screen.Write(0, sy+h, '├')
                self.Screen.Write(sze[0]-1, sy+h, '┤')
            sx = 0
            for xidx, w in enumerate(row+[None]):
                if self.mode == ScreenModes.LAYOUT:
                    txt = self.grid[yidx][xidx]
                    thisSel = False
                    if self.selected is not None and self.focus[0] == xidx and self.focus[1] == yidx:
                        thisSel = True
                        txt = self.selected
                    if txt is not None:
                        if w is None:
                            w = sze[0]-sx
                        lines = txt.split('\n')
                        midy = sy+max(h-len(lines)+1-int(thisSel)*2, 0)//2
                        for idx, ln in enumerate(lines[:h]):
                            self.Screen.Write(sx+max(w-len(ln)-int(thisSel)*2, 0)//2, midy+idx, ln[:w])
                if w is not None:
                    sx += w
                    chr = self.Screen.Get(sx, sy)
                    if chr == '┴':
                        self.Screen.Write(sx, sy, '┼')
                    elif chr != '+':
                        self.Screen.Write(sx, sy, '┬')
                    self.Screen.Write(sx, sy+h, '┴')
                    for iy in range(1+sy, sy+h):
                        self.Screen.Write(sx, iy, '│')
            sy += h
        
        if self.mode == ScreenModes.LAYOUT:
            hs = [i[1] for i in self.layout[:-1]]
            hs += [sze[1]-sum(hs+[0])-1]
            ws = self.layout[self.focus[1]][0].copy()
            ws += [sze[0]-sum(ws+[0])]
            y = 0
            mxy = sum(hs[:self.focus[1]+1]+[0])
            extra = '27;103;30' if (self.selected is not None) else '7'
            for y in range(sum(hs[:self.focus[1]]+[0]), mxy+1):
                x1 = sum(ws[:self.focus[0]]+[0])
                x2 = min(sum(ws[:self.focus[0]+1]+[0]), sze[0]-1)
                if y == mxy:
                    self.Screen.Write(x1, y, f'\033[{extra}m', self.Screen.Get(x1, y))
                    self.Screen.Write(x2, y, '+\033[0m')
                else:
                    self.Screen.Write(x1, y, '\033[7m', self.Screen.Get(x1, y))
                    self.Screen.Write(x2, y, f'\033[{extra}m{self.Screen.Get(x2, y)}\033[0m')
    
    def print(self):
        self._print_borders()
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
        self._print_borders()
        winSize = self.get_terminal_size()
        for y in range(winSize[1]):
            if y in self.Screen.screen:
                new = str(self.Screen.screen[y])
            else:
                new = ''
            
            sys.stdout.write(f'\033[{y+1};1H\033[K'+new[:winSize[0]+ANSILen(new)])
    
    @staticmethod
    def get_terminal_size():
        sze = shutil.get_terminal_size()
        return sze.columns, sze.lines

class Position:
    def __call__(self, size, winSzefun, parentFull):
        return (0, 0)

class StaticPos(Position):
    def __init__(self, x, y):
        self.x, self.y = x, y
    
    def __call__(self, size, winSzefun, parentFull):
        return (self.x, self.y)

class RelativePos(Position):
    def __init__(self, weight_x, weight_y, force_x=None, force_y=None):
        self.weight = (weight_x, weight_y)
        self.force = (force_x, force_y)
    
    def __call__(self, size, winSze, parentFull):
        out = []
        for i in range(2):
            if self.force[i] is not None:
                out.append(self.force[i])
            else:
                out.append(round((winSze[i]-size[i]-2)*self.weight[i]))
        return out

class Container:
    DRAW_WHILE_FULL = False
    
    API = TerminalAPI()

    def __new__(cls, *args, **kwargs):
        elm = super().__new__(cls)
        cls.API.elms.append(elm)
        return elm

    def __del__(self):
        if self.isFullscreen:
            self.unfullscreen()
        if self in self.API.elms:
            self.API.elms.remove(self)
    
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
    
    def extend(self, elms):
        super().extend([i(self.parent) for i in elms])
    
    def __getitem__(self, idx):
        if isinstance(idx, slice):
            new = ContainerWidgets(self.parent)
            new += super().__getitem__(idx)
            return new
        return super().__getitem__(idx)

class Widget:
    parent: Container

    def __new__(cls, *args, **kwargs):
        sup_new = super().__new__
        def new(parent):
            elm = sup_new(cls)
            elm.parent = parent
            elm.__init__(*args, **kwargs)
            return elm
        return new
    
    def __del__(self):
        if self in self.parent.widgets:
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
    width: int
    height: int

    def __init__(self, pos: Position):
        self._pos = pos
    
    @property
    def pos(self):
        return self._pos((self.width, self.height), self.API.get_terminal_size, self.parent.isFullscreen)
    
    @property
    def realPos(self):
        x, y = self._pos((self.width, self.height), self.API.get_terminal_size, self.parent.isFullscreen)
        return x+self.parent.x, y+self.parent.y

class Window(Container):
    def __init__(self, x, y, *widgets):
        self.x = x
        self.y = y
        self.widgets = ContainerWidgets(self, widgets)
        self.Screen = Screen()
        self._oldpos = None
        self._width = 0
        self._height = 0
        self._grabbed = None
        self._moved = False
    
    def draw(self):
        self.Screen.Clear()
        for widget in self.widgets:
            widget.draw()
        
        if self.Screen.screen == {}:
            lines = []
        else:
            lines = ["" for _ in range(max(self.Screen.screen.keys())+1)]
        for idx, line in self.Screen.screen.items():
            lines[idx] = str(line)

        isFull = self.isFullscreen
        if isFull:
            width, height = self.API.get_terminal_size()
            width -= 2
            height -= 2
        else:
            width, height = max(strLen(i) for i in (lines or [''])), len(lines)
        x, y = self.x, self.y
        self._width = width
        self._height = height
        if isFull:
            self._Write(width, 0, ']X')
            for idx, ln in enumerate(lines):
                self._Write(x+1, y+idx+1, ln)
        else:
            self._Write(x, y, '╭', '─'*(width-1), '[X')
            for idx, ln in enumerate(lines):
                self._Write(x, y+idx+1, '│', *split(ln)[:self.size[0]-2], " "*(width-strLen(ln)), '\033[0m│')
            t = '│'+' '*width+'│'
            for idx in range(len(lines), height):
                self._Write(x, y+idx+1, t)
            self._Write(x, y+height+1, '╰', '─'*width, '╯')
    
    @property
    def width(self):
        return self._width + 2
    @property
    def height(self):
        return self._height + 2
    
    def fullscreen(self):
        self._oldpos = (self.x, self.y)
        self.x, self.y = 0, 0
        return super().fullscreen()
    
    def unfullscreen(self):
        if self._oldpos is not None:
            self.x, self.y = self._oldpos
        return super().unfullscreen()
    
    def update(self):
        ret = False
        for wid in self.widgets:
            if wid.update():
                ret = True
        return ret

    def __str__(self):
        return '<Window object>'
    def __repr__(self): return str(self)

class ResizableWindow(Window):
    def __init__(self, x, y, startWid, startHei, *widgets):
        super().__init__(x, y, *widgets)
        self.size = (startWid, startHei)
        self._grabbingSize = None
    
    def draw(self):
        self.Screen.Clear()
        for widget in self.widgets:
            widget.draw()
        
        if self.Screen.screen == {}:
            lines = []
        else:
            lines = ["" for _ in range(max(self.Screen.screen.keys())+1)]
        for idx, line in self.Screen.screen.items():
            lines[idx] = str(line)
        
        x, y = self.x, self.y
        if self.isFullscreen:
            width, height = self.API.get_terminal_size()
            self._Write(width-2, 0, ']X')
            for idx, ln in enumerate(lines):
                self._Write(x+1, y+idx+1, ln)
        else:
            self._Write(x, y, '╭', '─'*(self.size[0]-3), '[X')
            for idx, ln in enumerate(lines[:self.size[1]-2]):
                self._Write(x, y+idx+1, '│', *split(ln)[:self.size[0]-2], " "*(self.size[0]-2-strLen(ln)), '\033[0m│')
            t = '│'+' '*(self.size[0]-2)+'│'
            for idx in range(len(lines), self.size[1]-2):
                self._Write(x, y+idx+1, t)
            self._Write(x, y+self.size[1]-1, '╰', '─'*(self.size[0]-2), '+')
    
    @property
    def width(self):
        if self.isFullscreen:
            return self.API.get_terminal_size()[0]
        return self.size[0]
    @property
    def height(self):
        if self.isFullscreen:
            return self.API.get_terminal_size()[1]
        return self.size[1]

    def update(self):
        return super().update()

class FullscreenWindow(Window):
    """
    A Window that MUST ALWAYS be fullscreen.
    """
    def __init__(self, *widgets):
        super().__init__(0, 0, *widgets)
        self.fullscreen()
    
    def unfullscreen(self):
        pass

    def draw(self):
        self.Screen.Clear()
        for widget in self.widgets:
            widget.draw()
        
        if self.Screen.screen == {}:
            lines = []
        else:
            lines = ["" for _ in range(max(self.Screen.screen.keys())+1)]
        for idx, line in self.Screen.screen.items():
            lines[idx] = str(line)

        isFull = self.isFullscreen
        if isFull:
            width, height = self.API.get_terminal_size()
            width -= 2
            height -= 2
        else:
            width, height = max(strLen(i) for i in (lines or [''])), len(lines)
        self._width = width
        self._height = height
        self._Write(width+1, 0, 'X')
        for idx, ln in enumerate(lines):
            self._Write(1, idx+1, f'{ln}{" "*(width-strLen(ln))}')

    def __del__(self):
        if self.isFullscreen:
            super().unfullscreen()
        if self in self.API.elms:
            self.API.elms.remove(self)
    
    def update(self):
        if not self.isFullscreen:
            if self.API.fullscreen is None:
                self.fullscreen()
        ret = False
        for wid in self.widgets:
            if wid.update():
                ret = True
        if self.API.LMB:
            if self._grabbed is None:
                if self.API.LMBP:
                    mpos = self.API.Mouse
                    if mpos[1] == self.y and self.x <= mpos[0] < (self.x+self.width):
                        self._moved = False
                        self._grabbed = mpos
            elif not self._moved:
                if self._grabbed != self.API.Mouse:
                    self._moved = True
        else:
            if not (self._moved or self._grabbed is None):
                if self._grabbed == (self.x+self.width-1, self.y):
                    self.__del__()
                    return True
            self._grabbed = None
        
        return ret

class Popup(Container):
    DRAW_WHILE_FULL = True
    
    def __init__(self, *widgets, duration=3, max_width=None):
        self.max_width = max_width
        self.widgets = ContainerWidgets(self, widgets)
        self.Screen = Screen()
        self.duration = duration
        self.start_time = time.time()
        self.x, self.y = None, None
    
    def draw(self):
        self.Screen.Clear()
        for widget in self.widgets:
            widget.draw()
        
        lines = ["" for _ in range(max(self.Screen.screen.keys())+1)]
        for idx, line in self.Screen.screen.items():
            lines[idx] = str(line)

        cols, rows = self.API.get_terminal_size()
        self.x, self.y = cols - max(strLen(i) for i in lines) - 2, rows - len(lines) - 2
        width, height = max(strLen(i) for i in (lines or [''])), len(lines)
        self._Write(self.x, self.y, '\033[100;34;1m│\033[39m', ' '*width, ' \033[0m')
        for idx, ln in enumerate(lines):
            self._Write(self.x, self.y+idx+1, f'\033[100;34;1m│\033[39{";22" if idx > 0 else ""}m{ln} {" "*(width-len(ln))}\033[0m')
        self._Write(self.x, self.y+height+1, '\033[100;34;1m│\033[39m', ' '*width, ' \033[0m')
    
    def update(self):
        if self.API.LMBP and self.x is not None and self.y is not None:
            mouse = self.API.Mouse
            if self.x <= mouse[0] and self.y <= mouse[1]:
                self.__del__()
                return True
        if time.time() - self.start_time > self.duration:
            self.__del__()
            return True
        return super().update()

class App:
    Win: ResizableWindow
    def __new__(cls, *args, **kwargs):
        inst = super().__new__(cls, *args, **kwargs)
        inst.Win = ResizableWindow(0, 0, 40, 10, *inst.init_widgets())
        return inst
    
    def init_widgets(self) -> list[Widget]:
        return []
    
    @property
    def widgets(self):
        return self.Win.widgets
    
    @widgets.setter
    def widgets(self, val):
        if isinstance(val, ContainerWidgets):
            self.Win.widgets = val
        else:
            self.Win.widgets = ContainerWidgets(self.Win, val)

class FullscreenApp(App):
    Win: FullscreenWindow
    def __new__(cls, *args, **kwargs):
        inst = object.__new__(cls, *args, **kwargs)
        inst.Win = FullscreenWindow(*inst.init_widgets())
        return inst
