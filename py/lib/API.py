from lib.IO import Key
from enum import IntEnum
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
        'Popup',
    'Widget',
        'PositionedWidget',
    'App'
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

class ScreenModes(IntEnum):
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
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.events: list[Key] = []
        self.allApps = []
        self.fullscreen = None
        self.focus = [0, 0]
        self.layout = [[[], None]]
        self.chooseHold = None
        self.grid = [[None]]
        self.extras = []
        self.selected = None
        self.searching = ''
        self.searchTxts = {}
        self.bottomTxt = ''
        self.mode = ScreenModes.APPS
        self.Screen = Screen()
        self._oldScreen = Screen()
    
    def allLoadedApps(self, container=None):
        if container is None:
            container = self.grid
        for i in container:
            if isinstance(i, list):
                yield from self.allLoadedApps(i)
            elif i is not None:
                yield i
    
    def _fixFocus(self):
        if self.focus[1] < 0:
            self.focus[1] = 0
        elif self.focus[1] >= len(self.layout):
            self.focus[1] = len(self.layout)-1
        
        if self.focus[0] < 0:
            self.focus[0] = 0
        elif self.focus[0] > len(self.layout[self.focus[1]][0]):
            self.focus[0] = len(self.layout[self.focus[1]][0])

    def updateAll(self):
        if self.mode == ScreenModes.APPS:
            for ev in self.events:
                if ev.state == 1:
                    if ev == 'super+A':
                        self.mode = ScreenModes.LAYOUT
                    # Arrow keys switch between
                    elif ev == 'super+UP':
                        self.focus[1] -= 1
                        self._fixFocus()
                    elif ev == 'super+DOWN':
                        self.focus[1] += 1
                        self._fixFocus()
                    elif ev == 'super+LEFT':
                        self.focus[0] -= 1
                        self._fixFocus()
                    elif ev == 'super+RIGHT':
                        self.focus[0] += 1
                        self._fixFocus()
            if self.fullscreen is not None:
                self.fullscreen.update(True)
                for elm in self.allLoadedApps():
                    if elm is not None and elm is not self.fullscreen and AppFlags.RunWhileFull in elm.FLAGS:
                        elm.update(False)
            else:
                focusApp = self.grid[self.focus[1]][self.focus[0]]
                if focusApp is not None:
                    focusApp.update(True)
                for elm in self.allLoadedApps():
                    if elm is not None and elm is not focusApp and AppFlags.Background in elm.FLAGS:
                        elm.update(False)
            for elm in self.extras:
                elm.update()
        elif self.mode == ScreenModes.LAYOUT:
            sze = self.get_terminal_size()
            for ev in self.events:
                if ev.state == 1:
                    if ev == 'ESC':
                        self.mode = ScreenModes.APPS
                    
                    # Creation - ctrl+<>
                    if ev == 'ctrl+W':
                        hei = (self.layout[self.focus[1]][1] or sze[1]-sum([i[1] for i in self.layout if i[1]]+[0]))/2
                        if hei >= 2:
                            self.grid.insert(self.focus[1], [None])
                            self.layout.insert(self.focus[1], [[], math.floor(hei)])
                            if self.focus[1]+1 < len(self.layout)-1:
                                self.layout[self.focus[1]+1][1] = math.ceil(hei)
                        self._fixFocus()
                    elif ev == 'ctrl+S':
                        hei = (self.layout[self.focus[1]][1] or sze[1]-sum([i[1] for i in self.layout if i[1]]+[0]))/2
                        if hei >= 2:
                            self.grid.insert(self.focus[1], [None])
                            self.layout.insert(self.focus[1], [[], math.ceil(hei)])
                            self.focus[1] += 1
                            if self.focus[1] < len(self.layout)-1:
                                self.layout[self.focus[1]][1] = math.floor(hei)
                            self._fixFocus()
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
                            self._fixFocus()
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
                            self._fixFocus()
                    
                    # Deletion - ctrl+alt+<>
                    elif ev == 'ctrl+alt+W':
                        if self.focus[1] != 0:
                            self.focus[1] -= 1
                            self.grid.pop(self.focus[1])
                            _, eh = self.layout.pop(self.focus[1])
                            if self.layout[self.focus[1]][1]:
                                self.layout[self.focus[1]][1] += eh
                            self._fixFocus()
                    elif ev == 'ctrl+alt+S':
                        if self.focus[1] < len(self.layout)-1:
                            self.grid.pop(self.focus[1])
                            _, eh = self.layout.pop(self.focus[1]+1)
                            self.layout[self.focus[1]][1] += eh
                            self._fixFocus()
                    elif ev == 'ctrl+alt+A':
                        if self.focus[0] > 0:
                            self.focus[0] -= 1
                            self.grid[self.focus[1]].pop(self.focus[0])
                            ew = self.layout[self.focus[1]][0].pop(self.focus[0])
                            if self.focus[0] < len(self.layout[self.focus[1]][0]):
                                self.layout[self.focus[1]][0][self.focus[0]] += ew
                            self._fixFocus()
                    elif ev == 'ctrl+alt+D':
                        if self.focus[0] == len(self.layout[self.focus[1]][0])-1:
                            self.grid[self.focus[1]].pop(-1)
                            self.layout[self.focus[1]][0].pop(-1)
                        elif self.focus[0] < len(self.layout[self.focus[1]][0])-1:
                            self.grid[self.focus[1]].pop(self.focus[0]+1)
                            ew = self.layout[self.focus[1]][0].pop(self.focus[0]+1)
                            self.layout[self.focus[1]][0][self.focus[0]] += ew
                        self._fixFocus()

                    # Arrow keys switch between
                    elif ev == 'UP':
                        self.focus[1] -= 1
                        self._fixFocus()
                    elif ev == 'DOWN':
                        self.focus[1] += 1
                        self._fixFocus()
                    elif ev == 'LEFT':
                        self.focus[0] -= 1
                        self._fixFocus()
                    elif ev == 'RIGHT':
                        self.focus[0] += 1
                        self._fixFocus()
                    
                    elif ev == 'SPACE' or (ev == 'ENTER' and self.selected is not None):
                        if self.selected is not None:
                            self.grid[self.focus[1]][self.focus[0]] = self.selected
                            self.selected = None
                        else:
                            self.selected = self.grid[self.focus[1]][self.focus[0]]
                            self.grid[self.focus[1]][self.focus[0]] = None
                    elif ev in ('BACKSPACE', 'DELETE'):
                        self.grid[self.focus[1]][self.focus[0]] = None
                    elif ev == 'ENTER':
                        self.mode = ScreenModes.APPS
                    elif ev == 'SLASH':
                        self.mode = ScreenModes.CHOOSE
                        self.searching = ''
                        self._search()
                
                # Just letters resize
                elif ev == 'W' and ev.heldFrames % 2 == 0:
                    if self.focus[1] < len(self.layout)-1:
                        if self.layout[self.focus[1]][1] > 3:
                            self.layout[self.focus[1]][1] -= 1
                            self._fixFocus()
                    elif self.focus[1] > 0:
                        h = sze[1]-sum(i[1] for i in self.layout if i[1])
                        if h > 3:
                            self.layout[self.focus[1]-1][1] += 1
                        self._fixFocus()
                elif ev == 'S' and ev.heldFrames % 2 == 0:
                    if self.focus[1] < len(self.layout)-1:
                        if sum(i[1] for i in self.layout if i[1])+1<(sze[1]-3):
                            self.layout[self.focus[1]][1] += 1
                            self._fixFocus()
                    elif self.focus[1] > 0 and self.layout[self.focus[1]-1][1] > 3:
                        self.layout[self.focus[1]-1][1] -= 1
                        self._fixFocus()
                elif ev == 'A':
                    if self.focus[0] < len(self.layout[self.focus[1]][0]) and self.layout[self.focus[1]][0][self.focus[0]] > 3:
                        self.layout[self.focus[1]][0][self.focus[0]] -= 1
                        self._fixFocus()
                    elif self.focus[0] > 0:
                        w = sze[0]-sum(self.layout[self.focus[1]][0])
                        if w > 3:
                            self.layout[self.focus[1]][0][self.focus[0]-1] += 1
                            self._fixFocus()
                elif ev == 'D':
                    if self.focus[0] < len(self.layout[self.focus[1]][0]):
                        if sum(self.layout[self.focus[1]][0])+1<(sze[0]-3):
                            self.layout[self.focus[1]][0][self.focus[0]] += 1
                            self._fixFocus()
                    elif self.focus[0] > 0 and self.layout[self.focus[1]][0][self.focus[0]-1] > 3:
                        self.layout[self.focus[1]][0][self.focus[0]-1] -= 1
                        self._fixFocus()
        elif self.mode == ScreenModes.CHOOSE:
            sze = self.get_terminal_size()
            MAX_LEN = round(sze[0]/5)
            MAX_LINES = round(sze[1]/5)
            FILLER = '⓿'
            if FILLER not in self.searching:
                self.searching += FILLER
            self.chooseHold = None
            MAP = {
                'u': 'ctrl+UP', 'd': 'ctrl+DOWN', 'l': 'ctrl+LEFT', 'r': 'ctrl+RIGHT'
            }
            heldevs = [i for i in self.events if i.state == 2]
            for idx, evs in enumerate([
                'ul', 'ur', 'dr', 'dl', 'u', 'r', 'd', 'l'
            ]):
                if all(MAP[i] in heldevs for i in evs):
                    self.chooseHold = idx
                    break
            change = False
            for ev in self.events:
                change_now = False
                if ev.state == 1:
                    if ev == 'ESC':
                        self.mode = ScreenModes.LAYOUT
                    elif ev in ('ctrl+ENTER', 'ctrl+shift+ENTER', 'ENTER', 'ctrl+LEFTSHIFT', 'ctrl+RIGHTSHIFT'):
                        if self.chooseHold in self.searchTxts:
                            self.grid[self.focus[1]][self.focus[0]] = self.searchTxts[self.chooseHold]()
                        self.mode = ScreenModes.LAYOUT
                    elif ev == 'UP':
                        self.searching = self.searching[:max(self.searching.index(FILLER)-MAX_LEN, 0)].replace(FILLER, '')+\
                                         FILLER+\
                                         self.searching[max(self.searching.index(FILLER)-MAX_LEN, 0):].replace(FILLER, '')
                    elif ev == 'DOWN':
                        self.searching = self.searching[:self.searching.index(FILLER)+MAX_LEN+1].replace(FILLER, '')+\
                                         FILLER+\
                                         self.searching[self.searching.index(FILLER)+MAX_LEN+1:].replace(FILLER, '')
                    elif ev == 'LEFT':
                        self.searching = self.searching[:max(self.searching.index(FILLER)-1, 0)].replace(FILLER, '')+\
                                         FILLER+\
                                         self.searching[max(self.searching.index(FILLER)-1, 0):].replace(FILLER, '')
                    elif ev == 'RIGHT':
                        self.searching = self.searching[:self.searching.index(FILLER)+2].replace(FILLER, '')+\
                                         FILLER+\
                                         self.searching[self.searching.index(FILLER)+2:].replace(FILLER, '')
                if ev.state == 1 or (ev.heldFor > 0.8 and ev.heldFrames % 4 == 0):
                    if ev == 'BACKSPACE':
                        self.searching = self.searching[:self.searching.index(FILLER)-1].replace(FILLER, '')+\
                                         FILLER+\
                                         self.searching[self.searching.index(FILLER)+1:].replace(FILLER, '')
                        change_now = True
                    elif ev == 'DELETE':
                        self.searching = self.searching[:self.searching.index(FILLER)].replace(FILLER, '')+\
                                         FILLER+\
                                         self.searching[self.searching.index(FILLER)+2:].replace(FILLER, '')
                        change_now = True
                    elif ev.unicode is not None:
                        self.searching = self.searching[:self.searching.index(FILLER)].replace(FILLER, '')+\
                                         ev.unicode+\
                                         FILLER+\
                                         self.searching[self.searching.index(FILLER)+1:].replace(FILLER, '')
                        change_now = True
                if change_now:
                    change = True
                    if FILLER not in self.searching:
                        self.searching = self.searching + FILLER
                    self.searching = self.searching[:MAX_LEN*MAX_LINES+1]

            if change:
                self._search()

    def _search(self):
        # txt = self.searching.replace('⓿', '')
        results = self.allApps
        self.searchTxts = {}
        for idx, res in enumerate(results[:4]): # First picks get edges
            self.searchTxts[idx+4] = res
        for idx, res in enumerate(results[4:8]): # Next picks get corners
            self.searchTxts[idx] = res

    def resetScreens(self):
        self._oldScreen, self.Screen = self.Screen, self._oldScreen
        self.Screen.Clear()
    
    def drawAll(self):
        if self.mode == ScreenModes.APPS:
            if self.fullscreen is not None:
                self.bottomTxt = ''
                self.fullscreen.draw()
            else:
                focusApp = self.grid[self.focus[1]][self.focus[0]]
                for elm in self.allLoadedApps():
                    if elm is not None and elm is not focusApp:
                        elm.draw()
                self.bottomTxt = ''
                if focusApp is not None: # Draw this last so it can set self.bottomTxt
                    focusApp.draw()
        elif self.mode == ScreenModes.CHOOSE:
            self.bottomTxt = 'ctrl+←↑→↓: choose | shift/enter: apply | esc: exit'
            sze = self.get_terminal_size()
            MAX_LEN = round(sze[0]/5)
            MAX_LINES = round(sze[1]/5)

            baselen = round(sze[0]/20)
            lens = {
                '|': baselen,
                '/': round(baselen*0.7),
                '\\': round(baselen*0.7),
                '-': baselen*2,
            }
            for idx, (chr, weight, dir) in enumerate([
                ('\\',(0, 0), (-1, -1)),
                ('/', (1, 0), (1, -1)),
                ('\\',(1, 1), (1, 1)),
                ('/', (0, 1), (-1, 1)),
                ('|', (0.5, 0), (0, -1)),
                ('-', (1, 0.5), (1, 0)),
                ('|', (0.5, 1), (0, 1)),
                ('-', (0, 0.5), (-1, 0)),
            ]):
                if idx not in self.searchTxts:
                    continue
                if self.chooseHold == idx:
                    txtFun = lambda t: f'\033[105;30m{t}\033[0m'
                else:
                    txtFun = lambda t: t
                for idx2 in range(lens[chr]):
                    self.Screen.Write(int((sze[0]-MAX_LEN)/2-1+(MAX_LEN+1)*weight[0]+dir[0]*idx2), int((sze[1]-MAX_LINES)/2-1+(MAX_LINES+1)*weight[1]+dir[1]*idx2), txtFun(chr))
                lines = str(self.searchTxts[idx]).split('\n')
                ml = max(len(i) for i in lines)
                sx = int((sze[0]-MAX_LEN  )/2-1+(MAX_LEN+1  )*weight[0]+dir[0]*lens[chr]+ml        *(weight[0]-1))
                sy = int((sze[1]-MAX_LINES)/2-1+(MAX_LINES+1)*weight[1]+dir[1]*lens[chr]+len(lines)*(weight[1]-1))
                for idx2, ln in enumerate(lines):
                    ptxt = txtFun(ln)
                    if idx2 == 0:
                        ptxt = f'\033[1m{ptxt}\033[0m'
                    self.Screen.Write(sx+(ml-len(ln))//2, sy+idx2, ptxt)
            
            lines = ['_'*MAX_LEN for _ in range(MAX_LINES)]
            for ln in range(min(math.ceil(len(self.searching)/MAX_LEN), MAX_LINES)):
                lnt = self.searching[ln*MAX_LEN:(ln+1)*MAX_LEN]
                tlen = (MAX_LEN-len(lnt))//2
                lines[ln] = ('_'*tlen+lnt+'_'*tlen+'_')[:MAX_LEN]
            midy = (sze[1]-len(lines)+1)//2
            for idx, ln in enumerate(lines):
                self.Screen.Write((sze[0]-len(ln))//2, midy+idx, '\033[0m', ln.replace('⓿', ['\033[7m_\033[27m', ' '][math.floor(time.time()%1.5)]))
        elif self.mode == ScreenModes.LAYOUT:
            self.bottomTxt = '←↑→↓: choose | WASD: resize | ctrl+WASD: create | ctrl+alt+WASD: remove | /: select app | space: move app | esc: exit'
    
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
                        lines = str(txt).split('\n')
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
        self.Screen.Write(sze[0]-1-len(self.bottomTxt), sze[1]-1, self.bottomTxt)
        
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
                    self.Screen.Write(x2, y, self.Screen.Get(x2, y), '\033[0m')
                else:
                    self.Screen.Write(x1, y, '\033[7m', self.Screen.Get(x1, y))
                    self.Screen.Write(x2, y, f'\033[{extra}m{self.Screen.Get(x2, y)}\033[0m')
        
        if self.mode == ScreenModes.APPS:
            hs = [i[1] for i in self.layout[:-1]]
            hs += [sze[1]-sum(hs+[0])-1]
            ws = self.layout[self.focus[1]][0].copy()
            ws += [sze[0]-sum(ws+[0])]
            y = 0
            mny = sum(hs[:self.focus[1]]+[0])
            mxy = sum(hs[:self.focus[1]+1]+[0])
            for y in range(mny, mxy+1):
                x1 = sum(ws[:self.focus[0]]+[0])
                x2 = min(sum(ws[:self.focus[0]+1]+[0]), sze[0]-1)
                if y == mny or y == mxy:
                    self.Screen.Write(x1, y, '\033[46;30m', self.Screen.Get(x1, y))
                    self.Screen.Write(x2, y, self.Screen.Get(x2, y), '\033[0m')
                else:
                    self.Screen.Write(x1, y, f'\033[46;30m{self.Screen.Get(x1, y)}\033[0m')
                    self.Screen.Write(x2, y, f'\033[46;30m{self.Screen.Get(x2, y)}\033[0m')
    
    def print(self):
        self._print_borders()
        if self.mode == ScreenModes.APPS:
            for elm in self.extras:
                elm.draw()
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
        if self.mode == ScreenModes.APPS:
            for elm in self.extras:
                elm.draw()
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
    def __call__(self, size, winSze):
        return (0, 0)

class StaticPos(Position):
    def __init__(self, x, y):
        self.x, self.y = x, y
    
    def __call__(self, size, winSze):
        return (self.x, self.y)

class RelativePos(Position):
    def __init__(self, weight_x, weight_y, force_x=None, force_y=None):
        self.weight = (weight_x, weight_y)
        self.force = (force_x, force_y)
    
    def __call__(self, size, winSze):
        out = []
        for i in range(2):
            if self.force[i] is not None:
                out.append(self.force[i])
            else:
                out.append(round((winSze[i]-size[i]-2)*self.weight[i]))
        return out

class WidgetMeta(type):
    def __new__(cls, name, bases, class_dict):
        new_class = super().__new__(cls, name, bases, class_dict)
        def newNew(cls, *args, **kwargs):
            def new(parent):
                elm = object.__new__(cls)
                elm.parent = parent
                elm.__init__(*args, **kwargs)
                return elm
            return new
        new_class.__new__ = newNew
        return new_class

class Widget(metaclass=WidgetMeta):
    parent: 'Container'
    
    def __del__(self):
        if self in self.parent.widgets:
            self.parent.widgets.remove(self)
    
    @property
    def API(self):
        return self.parent.API
    
    def draw(self, focus):
        pass

    def update(self, focus):
        pass
    
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
    
    def pos(self):
        return self._pos((self.width, self.height), self.parent.Size())

class WidgetContainer(list):
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
            new = WidgetContainer(self.parent)
            new += super().__getitem__(idx)
            return new
        return super().__getitem__(idx)

class Container:
    API = TerminalAPI()
    Screen: Screen

    def Size(self):
        return 0, 0

class Popup(Container):
    def __new__(cls, *args, **kwargs):
        inst = super().__new__(cls)
        cls.API.extras.append(inst)
        return inst
    
    def __del__(self):
        if self in self.API.extras:
            self.API.extras.remove(self)
    
    def __init__(self, *widgets, duration=3, max_width=None):
        self.max_width = max_width
        self.widgets = WidgetContainer(self, widgets)
        self.Screen = Screen()
        self.duration = duration
        self.start_time = time.time()
        self.width, self.height = 0, 0
    
    def Size(self):
        return self.width, self.height
    
    def draw(self):
        self.Screen.Clear()
        for widget in self.widgets:
            widget.draw(False)
        
        lines = ["" for _ in range(max(self.Screen.screen.keys())+1)]
        for idx, line in self.Screen.screen.items():
            lines[idx] = str(line)

        cols, rows = self.API.get_terminal_size()
        x, y = cols - max(strLen(i) for i in lines) - 2, rows - len(lines) - 2
        self.width, self.height = max(strLen(i) for i in (lines or [''])), len(lines)
        self.API.Screen.Write(x, y, '\033[100;34;1m│\033[39m', ' '*self.width, ' \033[0m')
        for idx, ln in enumerate(lines):
            self.API.Screen.Write(x, y+idx+1, f'\033[100;34;1m│\033[39{";22" if idx > 0 else ""}m{ln} {" "*(self.width-len(ln))}\033[0m')
        self.API.Screen.Write(x, y+self.height+1, '\033[100;34;1m│\033[39m', ' '*self.width, ' \033[0m')
    
    def update(self):
        if time.time() - self.start_time > self.duration:
            self.__del__()

class AppMeta(type):
    def __new__(cls, name, bases, class_dict):
        new_class = super().__new__(cls, name, bases, class_dict)
        if bases != (Container,) and bases != ():
            new_class.API.allApps.append(new_class)
        
        def nDel(self):
            getattr(new_class, '__del__', cls.__del__)(self)
        new_class.__del__ = nDel

        if not hasattr(new_class, 'FLAGS'):
            new_class.FLAGS = []
        
        return new_class

    def __str__(cls):
        return getattr(cls, 'NAME', super().__str__())
    def __repr__(cls):
        if not hasattr(cls, 'NAME'):
            return super().__repr__()
        return f'<App {cls.NAME}>'

class AppFlags(IntEnum):
    Background = 0
    """This app still updates even when not the focus"""
    RunWhileFull = 1
    """The app still runs even when another app is in fullscreen"""

class App(Container, metaclass=AppMeta):
    NAME = 'DEFAULT APP'
    FLAGS: list[AppFlags]
    def __init__(self, widgets=None):
        self.Screen = None
        self.focus = False
        self.focusElm = 0
        self.widgets = WidgetContainer(self, widgets or [])
    
    def _gridPos(self):
        for yidx, row in enumerate(self.API.grid):
            if self in row:
                return yidx, row.index(self)
    
    def Size(self, gridP=None):
        if gridP is None:
            y, x = self._gridPos()
        else:
            y, x = gridP
        thisrow = self.API.layout[y]
        tsze = self.API.get_terminal_size()
        if thisrow[1] is None:
            hei = tsze[1]-sum(i[1] for i in self.API.layout if i[1] is not None)
        else:
            hei = thisrow[1]
        
        if x >= len(thisrow[0]):
            wid = tsze[0]-sum(thisrow[0])
        else:
            wid = thisrow[0][x]
        
        return wid, hei
    
    def Pos(self, gridP=None):
        if gridP is None:
            y, x = self._gridPos()
        else:
            y, x = gridP
        return sum(self.API.layout[y][0][:x] or [0]), sum([i[1] for i in self.API.layout[:y]] or [0])
    
    def draw(self):
        self.Screen = Screen()
        for idx, w in enumerate(self.widgets):
            w.draw(self.focusElm == idx)
        
        gridP = self._gridPos()
        x, y = self.Pos(gridP)
        wid, hei = self.Size(gridP)
        for idx, ln in self.Screen.screen.items():
            if idx <= hei-2:
                self.API.Screen.Write(x+1, y+idx+1, *ln[:wid-2])

    def update(self, focus):
        self.focus = focus
        changed = False
        if self.focus:
            for ev in self.API.events:
                if ev.state == 1:
                    if ev == 'ctrl+RIGHT' or ev == 'TAB':
                        self.focusElm = min(self.focusElm+1, len(self.widgets)-1)
                        changed = True
                    elif ev == 'ctrl+LEFT' or ev == 'shift+TAB':
                        self.focusElm = max(self.focusElm-1, 0)
                        changed = True
        if changed:
            for ev in self.API.events:
                ev.heldFrames = 0
                ev.startHoldTime = time.time()
        for idx, w in enumerate(self.widgets):
            w.update(self.focusElm == idx)
    
    def __str__(self):
        return AppMeta.__str__(self.__class__)
    def __repr__(self):
        return AppMeta.__repr__(self.__class__)
