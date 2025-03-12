import sys
import tty
import termios
from lib.IO import KbdInp
from lib.API import TerminalAPI

API = TerminalAPI()
# API.elms.append(ResizableWindow(10, 10, 100, 100))

inp = KbdInp()
sys.stdout.write('\033[?25l')
sys.stdout.flush()

fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)
tty.setraw(fd)
sys.stdout.write('\033[2J\033[H')
force_redraw = True
while True:
    API.events = inp.handleQueue()
    # print(''.join(repr(i)+'\n' for i in API.events), end='')
    
    if API.updateAll() or force_redraw:
        API.resetScreens()
        
        API.drawAll()
        API.print()
        sys.stdout.flush()
        force_redraw = False
