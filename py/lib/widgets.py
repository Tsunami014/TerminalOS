import re
from lib.API import PositionedWidget, SPL, Row, TerminalScreen
from multiprocessing import Process, Queue
from queue import Empty
import math
import time
import os
import pty
import select
import fcntl
import struct
import termios
import sys

__all__ = [
    'Text', 
    'Button', 
    'TextInput'
]

def findLines(text, max_width):
    text = Row(SPL(text))
    if max_width:
        lines = []
        for paragraph in text.split('\n'):
            while len(paragraph) > max_width:
                space_index = paragraph.rfind(' ', end=max_width)
                if space_index == -1:
                    space_index = max_width
                lines.append(paragraph[:space_index]+[paragraph[space_index][:-1]])
                paragraph = paragraph[space_index+1:]
            lines.append(paragraph)
        return lines
    else:
        return text.split('\n')

class Text(PositionedWidget):
    def __init__(self, pos, text, max_width=None):
        super().__init__(pos)
        self.width, self.height = 0, 0
        self.text = text
        self.max_width = max_width
    
    def draw(self, focus):
        lines = findLines(self.text, self.max_width)
        
        self.width, self.height = max(len(i) for i in lines), len(lines)

        x, y = self.pos()
        
        for idx, ln in enumerate(lines):
            line = str(ln)
            if focus:
                line = f'\033[7m{line}\033[27m'
            self._Write(x, y+idx, line)

class Button(Text):
    def __init__(self, pos, text, callback, max_width=None):
        super().__init__(pos, text, max_width)
        self.callback = callback
        self.pressing = False
    
    def draw(self, focus):
        lines = findLines(self.text, self.max_width)
        self.width, self.height = max(len(i) for i in lines)+2, len(lines)+1

        if self.pressing:
            col = '43'
        elif focus:
            col = '45'
        else:
            col = '44'
        
        lines = [f'\033[{col}m {str(i)}{" "*(self.width-len(i)-1)}\033[49m' for i in lines] + [f'\033[{col}m'+'_'*self.width+'\033[49m']

        x, y = self.pos()
        for idx, line in enumerate(lines):
            self._Write(x, y+idx, line)
    
    def update(self, focus):
        self.pressing = False
        for ev in self.API.events:
            if focus and (ev == 'ENTER' or ev == 'SPACE'):
                if ev.state == 0:
                    self.callback()
                else:
                    self.pressing = True

class TextInput(PositionedWidget):
    FILLER = '⓿'
    def __init__(self, 
                 pos, 
                 max_width=None, 
                 max_height=None, 
                 show_lines=True, 
                 multiline=True, 
                 onenter=None, 
                 weight_lr=0.5, 
                 placeholder='', 
                 start=''
        ):
        super().__init__(pos)
        self.max_width = max_width
        self.max_height = max_height
        self.show_lines = show_lines
        self.placeholder = placeholder
        self.weight = weight_lr
        self.multiline = multiline
        self.onenter = onenter
        self.text = start
        self.cursor = None
        self.width, self.height = 0, 0
    
    def draw(self, focus):
        txt = self.text
        if not focus:
            txt = txt.replace(self.FILLER, '')
        if txt == '':
            if self.placeholder != '':
                lines = [f'\033[90m{i}\033[39m' for i in findLines(self.placeholder, self.max_width)]
            else:
                lines = [Row('_')]
        else:
            lines = findLines(txt, self.max_width)
        if self.show_lines and self.max_width is not None:
            # '\033[90m_\033[0m'
            nlines = lines[:self.max_height]
            if self.max_height is not None:
                nlines += [Row() for _ in range(self.max_height-len(nlines))]
            for idx, ln in enumerate(nlines):
                lnt = ln[:self.max_width]
                tlen = round((self.max_width-len(lnt))*self.weight)
                nlines[idx] = (Row('_'*tlen)+lnt+['_']*tlen+['_'])[:self.max_width]
        else:
            ml = max(len(i) for i in lines)
            if self.show_lines and self.max_height is not None:
                nlines = []
                for ln in range(self.max_height):
                    lnt = (lines[ln] if ln < len(lines) else ['_'])
                    midx = round((ml-len(lnt)) * self.weight)
                    nlines.append(Row(' '*midx)+lnt)
            else:
                nlines = []
                for ln in lines:
                    midx = round((ml-len(ln)) * self.weight)
                    nlines.append(Row(' '*midx)+ln)
        self.width = max(len(i) for i in nlines)
        self.height = len(nlines)
        x, y = self.pos()
        tme = math.floor(time.time()%1.5)
        for idx, ln in enumerate(nlines):
            self._Write(x, y+idx, str(ln).replace(self.FILLER, ['\033[7m_\033[27m', ' '][tme]))
    
    def update(self, focus):
        if self.FILLER not in self.text:
            self.text += self.FILLER
        for ev in self.API.events:
            if focus:
                change_now = False
                if ev.state == 1:
                    if ev == 'UP':
                        if self.max_width is None:
                            self.text = self.FILLER+self.text.replace(self.FILLER, '')
                        else:
                            self.text = self.text[:max(self.text.index(self.FILLER)-self.max_width, 0)].replace(self.FILLER, '')+\
                                             self.FILLER+\
                                             self.text[max(self.text.index(self.FILLER)-self.max_width, 0):].replace(self.FILLER, '')
                    elif ev == 'DOWN':
                        if self.max_width is None:
                            self.text = self.text.replace(self.FILLER, '')+self.FILLER
                        else:
                            self.text = self.text[:self.text.index(self.FILLER)+self.max_width+1].replace(self.FILLER, '')+\
                                             self.FILLER+\
                                             self.text[self.text.index(self.FILLER)+self.max_width+1:].replace(self.FILLER, '')
                    elif ev == 'LEFT':
                        self.text = self.text[:max(self.text.index(self.FILLER)-1, 0)].replace(self.FILLER, '')+\
                                         self.FILLER+\
                                         self.text[max(self.text.index(self.FILLER)-1, 0):].replace(self.FILLER, '')
                    elif ev == 'RIGHT':
                        self.text = self.text[:self.text.index(self.FILLER)+2].replace(self.FILLER, '')+\
                                         self.FILLER+\
                                         self.text[self.text.index(self.FILLER)+2:].replace(self.FILLER, '')
                if ev.state == 1 or (ev.heldFor > 0.8 and ev.heldFrames % 4 == 0):
                    if ev == 'BACKSPACE':
                        self.text = self.text[:self.text.index(self.FILLER)-1].replace(self.FILLER, '')+\
                                         self.FILLER+\
                                         self.text[self.text.index(self.FILLER)+1:].replace(self.FILLER, '')
                        change_now = True
                    elif ev == 'DELETE':
                        self.text = self.text[:self.text.index(self.FILLER)].replace(self.FILLER, '')+\
                                         self.FILLER+\
                                         self.text[self.text.index(self.FILLER)+2:].replace(self.FILLER, '')
                        change_now = True
                    elif ev == 'ENTER':
                        if self.multiline:
                            self.text = self.text[:self.text.index(self.FILLER)].replace(self.FILLER, '')+\
                                             '\n'+\
                                             self.FILLER+\
                                             self.text[self.text.index(self.FILLER)+1:].replace(self.FILLER, '')
                        if self.onenter is not None:
                            self.onenter()
                    elif ev.unicode is not None:
                        self.text = self.text[:self.text.index(self.FILLER)].replace(self.FILLER, '')+\
                                         ev.unicode+\
                                         self.FILLER+\
                                         self.text[self.text.index(self.FILLER)+1:].replace(self.FILLER, '')
                        change_now = True
                if change_now:
                    if self.FILLER not in self.text:
                        self.text = self.text + self.FILLER
                    if self.max_width is not None and self.max_height is not None:
                        self.text = self.text[:self.max_width*self.max_height+1]

class Terminal(PositionedWidget):
    def __init__(self, pos, cmd, width=50, height=10):
        self.width = width
        self.height = height
        
        self.master_fd = None
        self.child_pid = None
        self.orig_stdin_attrs = None

        self.Tscreen = TerminalScreen(width, height)

        self.updateQ = Queue()
        self.displQ = Queue()
        self.thread = Process(target=self.process, args=(self.updateQ, self.displQ, sys.stdin.fileno(), cmd, height, width), daemon=True)
        self.thread.start()
    
        super().__init__(pos)
    
    @staticmethod
    def process(updQ: Queue, dispQ: Queue, stdinFileNo, cmd, height, width):
        # Vars
        focus = False

        # Create pseudo-terminal
        master_fd, slave_fd = pty.openpty()
        winsize = struct.pack("HHHH", height, width, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

        pid = os.fork()
        if pid == 0:  # Child process
            # Child process: create new session, connect stdio to slave_fd, and exec the shell.
            os.close(master_fd)
            os.setsid()
            os.dup2(slave_fd, 0)  # stdin
            os.dup2(slave_fd, 1)  # stdout
            os.dup2(slave_fd, 2)  # stderr
            os.execlp(cmd, cmd, "-i") # This blocks forever when successful
        else:
            os.close(slave_fd)
            while True:
                try:
                    typ, dat = updQ.get_nowait()
                    if typ == 1:
                        focus = dat
                    elif typ == 2:
                        width, height = dat
                        winsize = struct.pack("HHHH", height, width, 0, 0)
                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                except Empty:
                    pass
                ls = [master_fd]
                if focus:
                    ls.append(stdinFileNo)
                rlist, _, _ = select.select(ls, [], [], 0.1)
                for fd in rlist:
                    if fd == master_fd:
                        # Read data from the pseudo-terminal.
                        try:
                            data = os.read(master_fd, 1024)
                        except OSError:
                            return
                        if not data:
                            return
                        # Feed the data to pyte to update the virtual screen.
                        dispQ.put(data.decode())
                    elif fd == stdinFileNo:
                        # Read key input from stdin.
                        key_data = os.read(stdinFileNo, 1024)
                        if key_data:
                            os.write(master_fd, key_data)
    
    def resize(self, width, height):
        if self.width == width or self.height == height:
            return
        self.updateQ.put((2, (width, height)))
        self.Tscreen.width, self.Tscreen.height = width, height
        self.width, self.height = width, height

    def update(self, focus):
        self.updateQ.put((1, focus))
        try:
            txt = self.displQ.get_nowait()
            self.Tscreen.WriteAtCur(txt.replace('\r\n', '\n'))
        except Empty:
            pass
    
    def draw(self, focus):
        x, y = self.pos()
        for y2, ln in self.Tscreen.screen.items():
            self._Write(x+1, y+y2+1, str(ln))
        if focus and math.floor(time.time()%1.5) == 0:
            x2, y2 = x+self.Tscreen.cursor[0]+1, y+self.Tscreen.cursor[1]+1
            self._Write(x2, y2, f'\033[7m{self._Screen.Get(x2, y2)}\033[27m')
