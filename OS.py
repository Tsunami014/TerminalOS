#!/usr/bin/python3
import os
import sys
import termios
import tty
import select
from queue import Queue, Empty
from threading import Thread

def get_terminal_size():
    rows, cols = os.popen('stty size', 'r').read().split()
    return int(rows), int(cols)

def draw_border(rows, cols):
    sys.stdout.write('\033[H')  # Move cursor to top-left
    sys.stdout.write('╭'+'─' * (cols-2)+'╮')  # Top border
    for row in range(2, rows):
        sys.stdout.write(f'\033[{row};1H│\033[{row};{cols}H│')  # Side borders
    sys.stdout.write(f'\033[{rows};1H╰' + '─' * (cols-2)+'╯')  # Bottom border
    sys.stdout.flush()

def clear_console():
    sys.stdout.write('\033[2J\033[0;0H')
    sys.stdout.flush()

class Pollable:
    def __init__(self, file):
        self.f = file
        self.fd = b''
        self.poll = select.poll()
        self.poll.register(file, select.POLLIN)
        self.readMoreData()
    
    def readMoreData(self):
        while self.poll.poll(1):
            self.fd += self.f.read(1)

    def read(self, size):
        if len(self.fd) < size:
            self.readMoreData()
            if len(self.fd) < size:
                return None
        data = self.fd[:size]
        self.fd = self.fd[size:]
        return data
    
    def __getitem__(self, idx):
        assert isinstance(idx, int)
        if len(self.fd) < idx:
            self.readMoreData()
            if len(self.fd) < idx:
                return False
        return True
    
    def __bool__(self):
        if not self.fd:
            self.readMoreData()
        return bool(self.fd)

class Readable:
    def __init__(self, file):
        self.f = file
        self.fd = ''
        self.q = Queue()
        t = Thread(target=self.enqueue_output, args=(self.f, self.q), daemon=True)
        t.start()
        self.readMoreData()
    
    @staticmethod
    def enqueue_output(out, queue):
        while True:
            queue.put(out.read(1))
    
    def readMoreData(self):
        try:
            line = self.q.get_nowait()
            self.fd += line
        except Empty:
            pass

    def read(self, size):
        if not self:
            return ''
        data = self.fd[:size]
        self.fd = self.fd[size:]
        return data
    
    def __getitem__(self, idx):
        assert isinstance(idx, int)
        if len(self.fd) < idx:
            self.readMoreData()
            if len(self.fd) < idx:
                return False
        return True
    
    def __bool__(self):
        if not self.fd:
            self.readMoreData()
        return bool(self.fd)

def main():
    clear_console()
    rows, cols = get_terminal_size()
    draw_border(rows, cols)

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setraw(fd)

    MOUSE = [0, 0]
    MOUSE_SENSITIVITY = [0.249, 0.13]
    run = True

    try:
        with open('/dev/input/mice', 'rb') as file:
            mouse = Pollable(file)
            stdin = Readable(sys.stdin)
            while run:
                while mouse[3]:
                    data = mouse.read(3)
                    status, dx, dy = data[0], data[1], data[2]
                    if dx > 127:
                        dx -= 256
                    if dy > 127:
                        dy -= 256
                    MOUSE[0] += dx*MOUSE_SENSITIVITY[0]
                    MOUSE[1] -= dy*MOUSE_SENSITIVITY[1]

                    tSize = get_terminal_size()
                    MOUSE[0] = max(1, min(tSize[1], MOUSE[0]))
                    MOUSE[1] = max(1, min(tSize[0], MOUSE[1]))

                    moveTo = f'\033[{round(MOUSE[1])};{round(MOUSE[0])}H'
                    sys.stdout.write(moveTo)
                    if status & 1:  # Left button clicked
                        sys.stdout.write(','+moveTo)
                
                while stdin:
                    char = stdin.read(1)
                    if char == '\x03' or char == '\x1b':  # Ctrl+C or ESC
                        run = False
                
                sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        clear_console()

if __name__ == '__main__':
    main()
