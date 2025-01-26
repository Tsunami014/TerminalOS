from API import Element, Window, strLen
import time

class TextWindow(Window):
    def __init__(self, x, y, text, max_width=None):
        super().__init__(x, y)
        self.max_width = max_width
        self._redrawNext = False
        self._oldText = text
        self._text = text
    
    @property
    def text(self):
        return self._text
    @text.setter
    def text(self, newText):
        if self._text != newText:
            self._redrawNext = True
            self._text = newText
    
    def update(self):
        resp = super().update() or self._redrawNext
        self._redrawNext = False
        return resp
    
    def draw(self):
        if self.max_width:
            lines = []
            for paragraph in self._text.split('\n'):
                while strLen(paragraph) > self.max_width:
                    space_index = paragraph.rfind(' ', 0, self.max_width)
                    if space_index == -1:
                        space_index = self.max_width
                    lines.append(paragraph[:space_index])
                    paragraph = paragraph[space_index:].lstrip()
                lines.append(paragraph)
        else:
            lines = self._text.split('\n')
        self._draw(lines)

class Popup(Element):
    def __init__(self, text, duration=3, max_width=None):
        self.max_width = max_width
        self.text = text
        self.duration = duration
        self.start_time = time.time()
        self.x, self.y = None, None
    
    def draw(self):
        if self.max_width:
            lines = []
            for paragraph in self.text.split('\n'):
                while strLen(paragraph) > self.max_width:
                    space_index = paragraph.rfind(' ', 0, self.max_width)
                    if space_index == -1:
                        space_index = self.max_width
                    lines.append(paragraph[:space_index])
                    paragraph = paragraph[space_index:].lstrip()
                lines.append(paragraph)
        else:
            lines = self.text.split('\n')

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
