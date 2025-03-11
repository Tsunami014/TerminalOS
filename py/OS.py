import sys
import tty
import termios
from lib.IO import Readable
from lib.API import TerminalAPI

API = TerminalAPI()
# API.elms.append(ResizableWindow(10, 10, 100, 100))

stdin = Readable(sys.stdin)
sys.stdout.write('\033[?25l')
sys.stdout.flush()

fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)
tty.setraw(fd)
sys.stdout.write('\033[2J\033[H')
force_redraw = True
while True:
    API.events = []
    while stdin:
        char = stdin.read(1)
        if char == '\x1b':  # Escape sequence detected
            sequence = char
            while True:
                next_char = stdin.read(1)
                if not next_char:
                    break
                sequence += next_char
                # Generally ends on alphadigit or ~
                if next_char.isalpha() or next_char == '~':
                    break
            API.events.append(sequence)
        else:
            API.events.append(char)
    
    if API.updateAll() or force_redraw:
        API.resetScreens()
        
        API.Screen.Write(10, 10, 'Hello! \033[1mBOLD\033[0m \033[7mINVERSE\033[0m \033[4mUNDERLINE\033[0m \033[5mBLINK\033[0m')

        API.drawAll()
        API.printAll()#print()
        sys.stdout.flush()
        force_redraw = False
