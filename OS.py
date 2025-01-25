#!/usr/bin/python3
import os
import sys
import termios
import tty
from IO import Pollable, Readable
from API import TerminalAPI, Element
from elements import TextWindow

API = TerminalAPI()
Element.API = API

WIND = TextWindow(10, 20, 'Hello, World!')

def draw_border():
    rows, cols = API.get_terminal_size()
    sys.stdout.write('\033[H')  # Move cursor to top-left
    sys.stdout.write('╭'+'─' * (cols-2)+'╮')  # Top border
    for row in range(2, rows):
        sys.stdout.write(f'\033[{row};1H│\033[{row};{cols}H│')  # Side borders
    sys.stdout.write(f'\033[{rows};1H╰' + '─' * (cols-2)+'╯')  # Bottom border

def clear_console():
    sys.stdout.write('\033[2J\033[0;0H')

def main():
    clear_console()
    draw_border()
    API.drawAll()
    sys.stdout.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)
    run = True

    API._RawMouse = [API.get_terminal_size()[1]/2, API.get_terminal_size()[0]/2]

    try:
        with open('/dev/input/mice', 'rb') as file:
            mouse = Pollable(file)
            stdin = Readable(sys.stdin)
            while run:
                redraw = False
                while mouse[3]:
                    redraw = True
                    data = mouse.read(3)
                    status, dx, dy = data[0], data[1], data[2]
                    if dx > 127:
                        dx -= 256
                    if dy > 127:
                        dy -= 256
                    API._RawMouse[0] += dx*API._MouseSensitivity[0]
                    API._RawMouse[1] -= dy*API._MouseSensitivity[1]

                    tSize = API.get_terminal_size()
                    API._RawMouse[0] = max(1, min(tSize[1], API._RawMouse[0]))
                    API._RawMouse[1] = max(1, min(tSize[0], API._RawMouse[1]))

                    API._MouseStatus = status
                
                while stdin:
                    char = stdin.read(1)
                    if char == '\x03' or char == '\x1b':  # Ctrl+C or ESC
                        run = False
                
                if API.updateAll():
                    redraw = True

                if redraw:
                    #clear_console()
                    draw_border()
                    API.drawAll()
                
                sys.stdout.write(API.moveToMouse)
                sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        clear_console()
        sys.stdout.flush()

if __name__ == '__main__':
    main()
