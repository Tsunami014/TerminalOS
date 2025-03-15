import sys
import tty
import termios
from lib.IO import KbdInp
from lib.API import TerminalAPI
import lib.core  # noqa: F401 # Imports all the apps which automatically add themselves to the API on definition

API = TerminalAPI()

inp = KbdInp()
sys.stdout.write('\033[?25l')
sys.stdout.flush()

fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)
tty.setraw(fd)
sys.stdout.write('\033[2J\033[H')
while True:
    evs = inp.handleQueue()
    resetCache = 'super+ctrl+shift+B' in evs
    API.events = evs
    
    API.updateAll()
    API.resetScreens()
    API.drawAll()
    if resetCache:
        API.printAll()
    else:
        API.print()
    sys.stdout.flush()
