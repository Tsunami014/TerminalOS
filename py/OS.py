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
while True:
    API.events = inp.handleQueue()
    
    API.updateAll()
    API.resetScreens()
    API.drawAll()
    API.print()
    sys.stdout.flush()
