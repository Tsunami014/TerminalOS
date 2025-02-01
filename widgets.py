from API import PositionedWidget, strLen

class Text(PositionedWidget):
    def __init__(self, x, y, text, max_width=None):
        super().__init__(x, y)
        self.width, self.height = 0, 0
        self.text = text
        self.max_width = max_width
    
    def processLines(self, lines):
        return lines
    
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
        if self.isHovering and self.API.LMB:
            self.callback(self)
            return True
        return False
