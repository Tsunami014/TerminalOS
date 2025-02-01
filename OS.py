#!/usr/bin/python3
import sys
import termios
import tty
from IO import Pollable, Readable
from API import TerminalAPI, Container, Border
from containers import Window, Popup
import widgets as wids

API = TerminalAPI()
Container.API = API

def clear_console():
    sys.stdout.write('\033[2J\033[H')

def main():
    Border()

    def update_text(btn):
        btn.parent.widgets[0].text = 'Clicked!'
    Window(10, 18, wids.Text(0, 0, 'Hello, World!'), wids.Button(0, 1, 'Click me!', update_text))
    Window(20, 5, wids.TextInput(0, 0, 20, 5, 'Type here!'))
    Popup(wids.Text(0, 0, 'This is a popup!\nHi!'), duration=5)

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
                while mouse[3]:
                    force_draw = True
                    data = mouse.read(3)
                    status, dx, dy = data[0], data[1], data[2]
                    if dx > 127:
                        dx -= 256
                    if dy > 127:
                        dy -= 256
                    API._RawMouse[0] += dx*API._MouseSensitivity[0]
                    API._RawMouse[1] -= dy*API._MouseSensitivity[1]

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
                        second = stdin.read(1)
                        if not second:
                            run = False  # Individual ESC key pressed, end
                        elif second == '[':
                            third = stdin.read(1)
                            API.events.append(char + second + third)
                        else:
                            API.events.append(char + second)
                    else:
                        API.events.append(char)
                
                if oldSize != (oldSize := API.get_terminal_size()):
                    clear_console()
                    API.Screen.Clear()
                    force_draw = True
                
                if API.updateAll() or force_draw:
                    API.drawAll()
                    mp = API.Mouse
                    sze = API.get_terminal_size()
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
