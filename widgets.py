from API import Widget, strLen

class Text(Widget):
    def __init__(self, x, y, text, max_width=None):
        self.x, self.y = x, y
        self.text = text
        self.max_width = max_width
    
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
        
        for idx, line in enumerate(lines):
            self._Write(self.x, self.y+idx, line)
