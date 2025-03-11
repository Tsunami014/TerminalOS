#!/usr/bin/python3
import sys
import termios
import tty
from lib.IO import Pollable, Readable
from lib.API import TerminalAPI, Container
import lib.core as core

API = TerminalAPI()
Container.API = API

def clear_console():
    sys.stdout.write('\033[2J\033[H')

def main():
    core.resetApps(API)

    # clear_console()
    API.drawAll()
    API.print()
    sys.stdout.write('\033[?25l')
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)
    run = True
    force_draw = True

    API._RawMouse = [API.get_terminal_size()[0]/2, API.get_terminal_size()[1]/2]

    try:
        with open('/dev/input/mice', 'rb') as file:
            mouse = Pollable(file)
            stdin = Readable(sys.stdin)
            oldSize = API.get_terminal_size()
            while run:
                API._prevMouse = [API.LMB, API.MMB, API.RMB]
                while mouse[3]:
                    force_draw = True
                    data = mouse.read(3)
                    status, dx, dy = data[0], data[1], data[2]
                    xsin = 1
                    ysin = 2
                    if dx > 127:
                        dx -= 256
                        xsin = -1
                    if dy > 127:
                        dy -= 256
                        ysin = -1
                    API._RawMouse[0] += abs(dx**1.25)*API._MouseSensitivity[0]*xsin
                    API._RawMouse[1] -= abs(dy**1.25)*API._MouseSensitivity[1]*ysin

                    tSize = API.get_terminal_size()
                    API._RawMouse[0] = max(-1, min(tSize[0], API._RawMouse[0]))
                    API._RawMouse[1] = max(-1, min(tSize[1], API._RawMouse[1]))

                    API._MouseStatus = status
                
                API.events = []
                while stdin:
                    char = stdin.read(1)
                    if char == '\x03':  # Ctrl+C
                        run = False
                    elif char == '\x1b':  # Escape sequence detected
                        sequence = char
                        while True:
                            next_char = stdin.read(1)
                            if not next_char:
                                break
                            sequence += next_char
                            # Generally ends on alphadigit or ~
                            if next_char.isalpha() or next_char == '~':
                                break
                        if sequence == '\x1b': # Just the escape key
                            run = False
                        else:
                            API.events.append(sequence)
                    else:
                        API.events.append(char)
                
                if oldSize != (oldSize := API.get_terminal_size()):
                    clear_console()
                    API.Screen.Clear()
                    force_draw = True
                
                if API.updateAll() or force_draw or True:
                    API.resetScreens()
                    sze = API.get_terminal_size()

                    API.Screen.Write(0, 0, '╭', '─' * (sze[0]-2), '╮')
                    for row in range(1, sze[1]-1):
                        API.Screen.Write(0, row, '│')
                        API.Screen.Write(sze[0]-1, row, '│')
                    API.Screen.Write(0, sze[1]-1, '╰', '─' * (sze[0]-2), '╯')

                    for id in range(1, 9):
                        totSze = 1
                        for elm in API.barElms:
                            if elm.BarNum == id:
                                if id in (1, 7):
                                    x = totSze
                                elif id in (2, 8):
                                    x = sze[0]-totSze
                                elif id in (3, 5):
                                    x = 0
                                else:
                                    x = sze[0]-1
                                
                                if id in (3, 4):
                                    y = totSze
                                elif id in (5, 6):
                                    y = sze[1]-totSze
                                elif id in (1, 2):
                                    y = 0
                                else:
                                    y = sze[1]-1
                                
                                totSze += elm.draw(x, y)
                    
                    API.drawAll()
                    
                    mp = API.Mouse
                    if mp[0] not in (-1, sze[0]) and mp[1] not in (-1, sze[1]+2):
                        API.Screen.Write(*mp, '\033[7m'+API.Screen.Get(*mp)+'\033[27m')

                    API.printAll()#print()
                    sys.stdout.flush()
                    force_draw = False
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        clear_console()
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()

if __name__ == '__main__':
    main()
