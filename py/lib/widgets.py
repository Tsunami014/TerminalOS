from lib.API import PositionedWidget, Clipboard, strLen, split
from multiprocessing import Process
import math
import time
import pyte
import os
import pty
import select
import fcntl
import struct
import termios
import signal
import sys

__all__ = [
    'Text', 
    'Button', 
    'TextInput'
]

def findLines(text, max_width):
    if max_width:
        lines = []
        for paragraph in text.split('\n'):
            while strLen(paragraph) > max_width:
                space_index = -1
                idx = 0
                realIdx = 0
                spl = split(paragraph)
                while realIdx < max_width and idx < len(spl):
                    if spl[idx][0] != '\033':
                        realIdx += 1
                    if spl[idx] == ' ':
                        space_index = realIdx
                    idx += 1
                if space_index == -1:
                    space_index = max_width
                lines.append(paragraph[:space_index])
                paragraph = paragraph[space_index:].lstrip()
            lines.append(paragraph)
    else:
        lines = text.split('\n')
    
    return lines

class Text(PositionedWidget):
    def __init__(self, pos, text, max_width=None):
        super().__init__(pos)
        self.width, self.height = 0, 0
        self.text = text
        self.max_width = max_width
    
    def draw(self, focus):
        lines = findLines(self.text, self.max_width)
        
        self.width, self.height = max(strLen(i) for i in lines), len(lines)

        x, y = self.pos()
        
        for idx, line in enumerate(lines):
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
        self.width, self.height = max(strLen(i) for i in lines)+2, len(lines)+1

        if self.pressing:
            col = '43'
        elif focus:
            col = '45'
        else:
            col = '44'
        
        lines = [f'\033[{col}m {i}{" "*(self.width-strLen(i)-1)}\033[49m' for i in lines] + [f'\033[{col}m'+'_'*self.width+'\033[49m']

        x, y = self.pos()
        for idx, line in enumerate(lines):
            self._Write(x, y+idx, line)
    
    def update(self, focus):
        self.pressing = False
        for ev in self.API.events:
            if focus and ev == 'ENTER' or ev == 'SPACE':
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
                lines = findLines(self.placeholder, self.max_width)
                lines = [f'\033[90m{i}\033[39m' for i in lines]
            else:
                lines = ['']
        else:
            lines = findLines(txt, self.max_width)
        if self.show_lines and self.max_width is not None:
            # '\033[90m_\033[0m'
            nlines = lines[:self.max_height]
            if self.max_height is not None:
                nlines += ['' for _ in range(self.max_height-len(nlines))]
            for idx, ln in enumerate(nlines):
                lnt = ln[:self.max_width]
                tlen = round((self.max_width-strLen(lnt))*self.weight)
                nlines[idx] = ('_'*tlen+lnt+'_'*tlen+'_')[:self.max_width]
        else:
            ml = max(strLen(i) for i in lines)
            if self.max_height is not None:
                nlines = []

                for ln in range(self.max_height):
                    lnt = (lines[ln] if ln < len(lines) else '_')
                    midx = round((ml-strLen(lnt)) * self.weight)

                    nlines.append(' '*midx+lnt+' '*(ml - midx - strLen(lnt)))
            else:
                nlines = []
                for ln in lines:
                    midx = round((ml-strLen(ln)) * self.weight)
                    nlines.append(' '*midx+ln+(ml - midx - strLen(ln)))
            
        self.width = max(strLen(i) for i in nlines)
        self.height = len(nlines)
        x, y = self.pos()
        tme = math.floor(time.time()%1.5)
        for idx, ln in enumerate(nlines):
            self._Write(x, y+idx, ln.replace(self.FILLER, ['\033[7m_\033[27m', ' '][tme]))
    
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

# TODO: Make faster, allow access to colours
class Terminal(PositionedWidget):
    def __init__(self, pos, cmd, width=50, height=10):
        self.height = height
        self.width = width
        self.cmd = cmd

        self.screen = pyte.Screen(width, height)
        self.stream = pyte.Stream(self.screen)
        
        self.master_fd = None
        self.child_pid = None
        self.orig_stdin_attrs = None
    
        super().__init__(pos)
        self.start()

    def start(self):
        """Start the virtual terminal."""
        # Create pseudo-terminal
        self.master_fd, slave_fd = pty.openpty()
        winsize = struct.pack("HHHH", self.height, self.width, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        
        # Fork a child process to run the shell
        pid = os.fork()
        if pid == 0:
            # Child process: create new session, connect stdio to slave_fd, and exec the shell.
            os.setsid()
            os.dup2(slave_fd, 0)  # stdin
            os.dup2(slave_fd, 1)  # stdout
            os.dup2(slave_fd, 2)  # stderr
            os.close(self.master_fd)
            os.execlp(self.cmd, self.cmd, "-i")
        else:
            # Parent process: close slave_fd, save child pid.
            self.child_pid = pid
            os.close(slave_fd)
    
    def resize(self, width, height):
        if self.width == width or self.height == height:
            return
        winsize = struct.pack("HHHH", height, width, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        os.kill(self.child_pid, signal.SIGWINCH)
        self.screen.resize(height, width)
        self.height = height
        self.width = width

    def update(self, focus):
        ls = [self.master_fd]
        if focus:
            ls.append(sys.stdin.fileno())
        rlist, _, _ = select.select(ls, [], [], 0.1)
        for fd in rlist:
            if fd == self.master_fd:
                # Read data from the pseudo-terminal.
                try:
                    data = os.read(self.master_fd, 1024)
                except OSError:
                    return
                if not data:
                    return
                # Feed the data to pyte to update the virtual screen.
                self.stream.feed(data.decode('utf-8', errors='ignore'))
            elif fd == sys.stdin.fileno():
                # Read key input from stdin.
                key_data = os.read(sys.stdin.fileno(), 1024)
                if key_data:
                    os.write(self.master_fd, key_data)
    
    def draw(self, focus):
        x, y = self.pos()
        for idx, ln in enumerate(self.screen.display):
            self._Write(x, y+idx, ln)
