from API import Container, strLen, Screen, ContainerWidgets
import time

__all__ = [
    'Window',
    'Popup'
]

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
        self._Write(x, y, '╭', '─'*(width-1), ('[' if not isFull else ']'), 'X')
        for idx, ln in enumerate(lines):
            self._Write(x, y+idx+1, f'│{ln}{" "*(width-strLen(ln))}│')
        for idx in range(len(lines), height):
            self._Write(x, y+idx+1, '│'+' '*width+'│')
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
                elif self._grabbed == (self.x+self.width-2, self.y):
                    if self.isFullscreen:
                        self.unfullscreen()
                    else:
                        self.fullscreen()
                    return True
            self._grabbed = None
        
        return ret

    def __str__(self):
        return '<Window object>'
    def __repr__(self): return str(self)

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
        if time.time() - self.start_time > self.duration:
            self.__del__()
            return True
        return super().update()
