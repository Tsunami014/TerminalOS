from API import PositionedWidget, strLen
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
                space_index = paragraph.rfind(' ', 0, max_width)
                if space_index == -1:
                    space_index = max_width
                lines.append(paragraph[:space_index])
                paragraph = paragraph[space_index:].lstrip()
            lines.append(paragraph)
    else:
        lines = text.split('\n')
    
    return lines

class Text(PositionedWidget):
    def __init__(self, x, y, text, max_width=None):
        super().__init__(x, y)
        self.width, self.height = 0, 0
        self.text = text
        self.max_width = max_width
    
    def processLines(self, lines):
        return lines
    
    def draw(self):
        lines = findLines(self.text, self.max_width)
        
        self.width, self.height = max(strLen(i) for i in lines), len(lines)

        lines = self.processLines(lines)
        
        for idx, line in enumerate(lines):
            self._Write(self.x, self.y+idx, line)

class Button(Text):
    def __init__(self, x, y, text, callback, max_width=None):
        super().__init__(x, y, text, max_width)
        self.callback = callback
    
    @property
    def isHovering(self):
        rp = self.realPos
        return self.API.Mouse[0] > rp[0] and self.API.Mouse[0] <= rp[0]+self.width and \
               self.API.Mouse[1] > rp[1] and self.API.Mouse[1] <= rp[1]+self.height+1
    
    def processLines(self, lines):
        if self.isHovering:
            return [f'\033[45m{i}\033[49m' for i in lines] + ['\033[45m'+'_'*self.width+'\033[49m']
        return [f'\033[44m{i}\033[49m' for i in lines] + ['\033[44m'+'_'*self.width+'\033[49m']
        # The linux vt doesn't support advanced colours :'(
        # if self.isHovering:
        #     return [f'\033[38;5;250;48;5;237m{i}\033[39;49m' for i in lines] + ['\033[48;5;237;38;5;246m'+'_'*self.width+'\033[39;49m']
        # return [f'\033[100m{i}\033[49m' for i in lines] + ['\033[100;38;5;250m'+'_'*self.width+'\033[39;49m']
    
    def update(self):
        if self.isHovering and self.API.LMBP:
            self.callback()
            return True
        return False

class TextInput(PositionedWidget):
    def __init__(self, x, y, max_width=None, max_height=None, placeholder='', start=''):
        super().__init__(x, y)
        self.max_width = max_width
        self.max_height = max_height
        self.placeholder = placeholder
        self.text = start
        self.cursor = None
    
    def draw(self):
        if self.text == '':
            lines = ['\033[90m'+self.placeholder+'\033[39m']
        else:
            lines = findLines(self.text, self.max_width)
        
        self.height = min(len(lines), self.max_height)
        self.width = max(strLen(i) for i in lines)
        
        for idx, line in enumerate(lines[:self.height]):
            self._Write(self.x, self.y+idx, line)
        

        if self.cursor is not None:
            self.fix_cursor(lines)
            self._Write(self.x+self.cursor[0], self.y+self.cursor[1], ('\033[4m' if round(time.time())%2 == 0 else ''), self._Screen.Get(*self.cursor), '\033[24m')
    
    def fix_cursor(self, lines=None):
        if self.text == '':
            self.cursor = [0, 0]
            return
        if lines is None:
            lines = findLines(self.text, self.max_width)
        self.cursor = [self.cursor[0], min(self.cursor[1], self.height)]
        self.cursor[0] = min(self.cursor[0], len(lines[self.cursor[1]]))
    
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
                while len(paragraph) > self.max_width:
                    space_index = paragraph.rfind(' ', 0, self.max_width)
                    if space_index == -1:
                        space_index = self.max_width
                    idx += len(paragraph[:space_index])
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
            idx = len("\n".join(self.text.split('\n')[:self.cursor[1]]))+self.cursor[0]
        return idx
    
    def update(self):
        if self.API.LMBP:
            if self.isHovering:
                rp = self.realPos
                self.cursor = self.API.Mouse[0]-rp[0]-1, self.API.Mouse[1]-rp[1]-1
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
                        idx = self.cursorIdx
                        self.text = self.text[:idx] + char + self.text[idx:]
                        if char == '\n':
                            self.cursor[1] += 1
                            self.cursor[0] = 0
                        else:
                            self.cursor[0] += 1
                    elif char == '\x7f':
                        # Backspace
                        did_something = True
                        idx = self.cursorIdx
                        if self.cursor != [0, 0]:
                            self.text = self.text[:idx-1] + self.text[idx:]
                        if self.cursor[0] == 0:
                            if self.cursor[1] != 0:
                                lines = findLines(self.text, self.max_width)
                                self.cursor[1] -= 1
                                self.cursor[0] = len(lines[self.cursor[1]])
                        else:
                            self.cursor[0] -= 1
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
