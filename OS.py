#!/usr/bin/python3
import os
import sys
import termios
import tty
from IO import Pollable, Readable

class TerminalAPI:
    def __init__(self):
        self._windows = []
        self.MOUSE = [0, 0]
        self.MOUSE_STATUS = 0
        self.MOUSE_SENSITIVITY = [0.249, 0.13]
    
    def add_window(self, window):
        self._windows.append(window)
    
    def remove_window(self, window):
        self._windows.remove(window)
    
    def drawAll(self):
        for window in self._windows:
            window.draw()
    
    @property
    def moveToMouse(self):
        return f'\033[{round(API.MOUSE[1])};{round(API.MOUSE[0])}H'
    
    @staticmethod
    def get_terminal_size():
        rows, cols = os.popen('stty size', 'r').read().split()
        return int(rows), int(cols)

API = TerminalAPI()

class Window:
    API = API
    def __new__(cls, *args, **kwargs):
        window = super().__new__(cls)
        cls.API.add_window(window)
        return window
    
    def __del__(self):
        self.API.remove_window(self)
    
    def draw(self):
        pass

    def __str__(self):
        return '<Window object>'
    def __repr__(self): return str(self)

class TextWindow(Window):
    def __init__(self, x, y, text, max_width=None):
        self.x = x
        self.y = y
        self.max_width = max_width
        self.text = text
    
    def draw(self):
        if self.max_width:
            lines = []
            for paragraph in self.text.split('\n'):
                while len(paragraph) > self.max_width:
                    space_index = paragraph.rfind(' ', 0, self.max_width)
                    if space_index == -1:
                        space_index = self.max_width
                    lines.append(paragraph[:space_index])
                    paragraph = paragraph[space_index:].lstrip()
                lines.append(paragraph)
        else:
            lines = self.text.split('\n')
        width, height = max(len(i) for i in lines), len(lines)
        sys.stdout.write(f'\033[{self.y};{self.x}H╭'+('─'*width)+'╮')
        for idx, ln in enumerate(lines):
            sys.stdout.write(f'\033[{self.y+idx+1};{self.x}H│{ln}│')
        sys.stdout.write(f'\033[{self.y+height+1};{self.x}H╰'+('─'*width)+'╯')

WIND = TextWindow(10, 20, 'Hello, World!')

def draw_border():
    rows, cols = API.get_terminal_size()
    sys.stdout.write('\033[H')  # Move cursor to top-left
    sys.stdout.write('╭'+'─' * (cols-2)+'╮')  # Top border
    for row in range(2, rows):
        sys.stdout.write(f'\033[{row};1H│\033[{row};{cols}H│')  # Side borders
    sys.stdout.write(f'\033[{rows};1H╰' + '─' * (cols-2)+'╯')  # Bottom border

def clear_console():
    sys.stdout.write('\033[2J\033[0;0H')

def main():
    clear_console()
    draw_border()
    API.drawAll()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)
    run = True

    API.MOUSE = [API.get_terminal_size()[1]//2, API.get_terminal_size()[0]//2]

    try:
        with open('/dev/input/mice', 'rb') as file:
            mouse = Pollable(file)
            stdin = Readable(sys.stdin)
            while run:
                update = False
                API.MOUSE_STATUS = 0
                while mouse[3]:
                    update = True
                    data = mouse.read(3)
                    status, dx, dy = data[0], data[1], data[2]
                    if dx > 127:
                        dx -= 256
                    if dy > 127:
                        dy -= 256
                    API.MOUSE[0] += dx*API.MOUSE_SENSITIVITY[0]
                    API.MOUSE[1] -= dy*API.MOUSE_SENSITIVITY[1]

                    tSize = API.get_terminal_size()
                    API.MOUSE[0] = max(2, min(tSize[1]-1, API.MOUSE[0]))
                    API.MOUSE[1] = max(2, min(tSize[0]-1, API.MOUSE[1]))

                    API.MOUSE_STATUS = status

                if API.MOUSE_STATUS & 1:  # Left button clicked
                    sys.stdout.write(API.moveToMouse+',')
                
                while stdin:
                    char = stdin.read(1)
                    if char == '\x03' or char == '\x1b':  # Ctrl+C or ESC
                        run = False
                
                if update:
                    #clear_console()
                    draw_border()
                    API.drawAll()
                
                sys.stdout.write(API.moveToMouse)
                sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        clear_console()
        sys.stdout.flush()

if __name__ == '__main__':
    main()
