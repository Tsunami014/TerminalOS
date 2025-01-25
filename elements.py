from API import Window

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
                while len(paragraph) > self.max_width:
                    space_index = paragraph.rfind(' ', 0, self.max_width)
                    if space_index == -1:
                        space_index = self.max_width
                    lines.append(paragraph[:space_index])
                    paragraph = paragraph[space_index:].lstrip()
                lines.append(paragraph)
        else:
            lines = self._text.split('\n')
        self._draw(lines)
