from lib.API import PositionedWidget, Clipboard, strLen, split
from string import printable
import time

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
    
    def draw(self):
        lines = findLines(self.text, self.max_width)
        
        self.width, self.height = max(strLen(i) for i in lines), len(lines)

        x, y = self.pos
        
        for idx, line in enumerate(lines):
            self._Write(x, y+idx, line)

class Button(Text):
    def __init__(self, pos, text, callback, max_width=None):
        super().__init__(pos, text, max_width)
        self.callback = callback
    
    @property
    def isHovering(self):
        rp = self.realPos
        return self.API.Mouse[0] > rp[0] and self.API.Mouse[0] <= rp[0]+self.width and \
               self.API.Mouse[1] > rp[1] and self.API.Mouse[1] <= rp[1]+self.height
    
    def draw(self):
        lines = findLines(self.text, self.max_width)
        
        self.width, self.height = max(strLen(i) for i in lines)+2, len(lines)+1

        if self.isHovering:
            lines = [f'\033[45m {i}{" "*(self.width-strLen(i)-1)}\033[49m' for i in lines] + ['\033[45m'+'_'*self.width+'\033[49m']
        else:
            lines = [f'\033[44m {i}{" "*(self.width-strLen(i)-1)}\033[49m' for i in lines] + ['\033[44m'+'_'*self.width+'\033[49m']
        # The linux vt doesn't support advanced colours :'(
        # if self.isHovering:
        #     lines = [f'\033[38;5;250;48;5;237m {i} \033[39;49m' for i in lines] + ['\033[48;5;237;38;5;246m'+'_'*self.width+'\033[39;49m']
        # lines = [f'\033[100m {i} \033[49m' for i in lines] + ['\033[100;38;5;250m'+'_'*self.width+'\033[39;49m']

        x, y = self.pos
        
        for idx, line in enumerate(lines):
            self._Write(x, y+idx, line)
    
    def update(self):
        if self.isHovering and self.API.LMBP:
            self.callback()
            return True
        return False

class TextInput(PositionedWidget):
    def __init__(self, pos, max_width=None, max_height=None, placeholder='', start=''):
        super().__init__(pos)
        self.max_width = max_width
        self.max_height = max_height
        self.placeholder = placeholder
        self.text = start
        self.cursor = None
        self.width, self.height = 0, 0
    
    def draw(self):
        if self.text == '':
            if self.placeholder != '':
                lines = findLines(self.placeholder, self.max_width)
                lines = [f'\033[90m{i}\033[39m' for i in lines]
            else:
                if self.max_width is not None:
                    lines = [' '*self.max_width]
                else:
                    lines = ['']
        else:
            lines = findLines(self.text, self.max_width)
        self.width = max(strLen(i) for i in lines)+1
        lines = [f'\033[4m{i + ' '*(self.width-strLen(i))}\033[24m' for i in lines]
        
        self.height = len(lines)
        if self.max_height:
            self.height = min(self.height, self.max_height)

        x, y = self.pos
        
        for idx, line in enumerate(lines[:self.height]):
            self._Write(x, y+idx, line)
        
        if self.cursor is not None:
            if self.text == '' and self.placeholder != '':
                newchar = '\033[39m|\033[90m'
            else:
                newchar = '|'
            self.fix_cursor(lines)
            chars = split(self._Screen.Get(x+self.cursor[0], y+self.cursor[1]))
            if round(time.time()*3)%3 != 0:
                for idx in range(len(chars)):
                    if chars[idx][0] != '\033':
                        chars[idx] = newchar
                        break
                else:
                    chars = [newchar]+chars
            else:
                if all(i[0] == '\033' for i in chars):
                    chars = [' ']+chars
            self._Write(x+self.cursor[0], y+self.cursor[1], *chars)
    
    def fix_cursor(self, lines=None, justCapX=False):
        if self.text == '':
            self.cursor = [0, 0]
            return
        if lines is None:
            lines = findLines(self.text, self.max_width)
        self.cursor = list(self.cursor)
        max_hei = min(len(lines)-1, self.max_height) if self.max_height is not None else (len(lines)-1)
        self.cursor[1] = min(max(self.cursor[1], 0), max_hei)
        if justCapX:
            self.cursor[0] = min(max(self.cursor[0], 0), len(lines[self.cursor[1]]))
        else:
            if self.cursor[0] < 0:
                self.cursor[1] -= 1
                if self.cursor[1] < 0:
                    self.cursor[1] = 0
                    self.cursor[0] = 0
                else:
                    self.cursor[0] = len(lines[self.cursor[1]])
            if self.cursor[0] > len(lines[self.cursor[1]]):
                self.cursor[1] += 1
                if self.cursor[1] > max_hei:
                    self.cursor[1] = max_hei
                    self.cursor[0] = len(lines[self.cursor[1]])
                else:
                    self.cursor[0] = 0
    
    @property
    def isHovering(self):
        rp = self.realPos
        return self.API.Mouse[0] > rp[0] and self.API.Mouse[0] <= rp[0]+self.width+1 and \
               self.API.Mouse[1] > rp[1] and self.API.Mouse[1] <= rp[1]+self.height
    
    @property
    def cursorIdx(self):
        if self.max_width:
            idx = 0
            y = 0
            for paragraph in self.text.split('\n'):
                while strLen(paragraph) > self.max_width:
                    space_index = paragraph.rfind(' ', 0, self.max_width)
                    if space_index == -1:
                        space_index = self.max_width
                    idx += space_index
                    y += 1
                    if y >= self.cursor[1]:
                        break
                    paragraph = paragraph[space_index:].lstrip()
                if y >= self.cursor[1]:
                    break
                idx += len(paragraph) + 1
                y += 1
                if y >= self.cursor[1]:
                    break
            idx += self.cursor[0]
        else:
            idx = len("".join(self.text.split('\n')[:self.cursor[1]]))+self.cursor[1]+self.cursor[0]
        return idx
    
    def update(self):
        if self.API.LMBP:
            if self.isHovering:
                rp = self.realPos
                mp = self.API.Mouse
                self.cursor = mp[0]-rp[0]-1, mp[1]-rp[1]-1
                self.fix_cursor(justCapX=True)
                return True
            else:
                self.cursor = None
        if self.cursor is not None:
            if self.API.events:
                for char in self.API.events:
                    did_something = False
                    if char in printable:
                        # A printable character
                        did_something = True
                        if char == '\r':
                            char = '\n'
                        if char == '\t':
                            self.API.events.extend([' ' for _ in range(4)])
                            continue
                        idx = self.cursorIdx
                        if char == '\n':
                            lines = findLines(self.text, self.max_width)
                            if self.max_height is not None and len(lines)+1 > self.max_height:
                                did_something = False
                                continue
                            self.cursor[1] += 1
                            self.cursor[0] = 0
                        else:
                            self.cursor[0] += 1
                        self.text = self.text[:idx] + char + self.text[idx:]
                    elif char == '\x7f': # Backspace
                        did_something = True
                        idx = self.cursorIdx
                        if idx != 0:
                            self.text = self.text[:idx-1] + self.text[idx:]
                            self.cursor[0] -= 1
                            self.fix_cursor()
                    elif char == '\x16': # Ctrl+V
                        did_something = True
                        self.API.events.extend(list(Clipboard.read()))
                    elif char[:2] == '\x1b[':
                        # An escape sequence
                        if char[2] == 'A':
                            # Up
                            did_something = True
                            self.cursor[1] -= 1
                        elif char[2] == 'B':
                            # Down
                            did_something = True
                            self.cursor[1] += 1
                        elif char[2] == 'C':
                            # Right
                            did_something = True
                            self.cursor[0] += 1
                        elif char[2] == 'D':
                            # Left
                            did_something = True
                            self.cursor[0] -= 1

                    if did_something:
                        self.fix_cursor()

            return True
        return False
