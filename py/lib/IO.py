from evdev import InputDevice, list_devices, categorize, ecodes
from queue import Empty
from multiprocessing import Process, Pipe

__all__ = ['Key', 'KbdInp']

def find_keyboard():
    for dev_path in list_devices():
        device = InputDevice(dev_path)
        if "keyboard" in device.name.lower() or "kbd" in device.name.lower():
            return device
    raise Exception("No keyboard device found. Try running as root.")

def scancode_to_unicode(scancode):
    try:
        key_name = ecodes.KEY[scancode]
        if key_name.startswith("KEY_"):
            return key_name[4:]
        return key_name
    except KeyError:
        return f"[{scancode}]"

class Key:
    def __init__(self, code, state, modifs):
        self.scancode = code
        self.state = state
        self.unicode = scancode_to_unicode(code)
        self.heldFor = 0
        self.shift = modifs['shift']
        self.ctrl = modifs['ctrl']
        self.alt = modifs['alt']
        self.super = modifs['super']
    
    def __str__(self):
        infset = self.unicode
        if self.super:
            infset = 'super+'+infset
        if self.ctrl:
            infset = 'ctrl+'+infset
        if self.alt:
            infset = 'alt+'+infset
        if self.shift:
            infset = 'shift+'+infset
        return infset
    def __repr__(self):
        return f'<Key event: {str(self)}: {["up", "down", "hold"][self.state]} held for {self.heldFor}>'
    
    def __eq__(self, other):
        if isinstance(other, Key):
            return all(getattr(self, i) == getattr(other, i) for i in ('scancode', 'state', 'shift', 'ctrl', 'alt', 'super'))
        infset = set((self.unicode,))
        if self.shift:
            infset.add('shift')
        if self.ctrl:
            infset.add('ctrl')
        if self.alt:
            infset.add('alt')
        if self.super:
            infset.add('super')
        return set(str(other).split('+')) == infset

class KbdInp:
    def __init__(self):
        self.fd = ''
        self.pipe, child = Pipe()
        self.pro = Process(target=self.getInp, args=(child,), daemon=True)
        self.pro.start()
        self.events = {}
    
    @staticmethod
    def getInp(pipe):
        device = find_keyboard()
        modifs = {
            'shift': False,
            'ctrl': False,
            'alt': False,
            'super': False,
        }

        while True:
            try:
                for event in device.read_loop():
                    if event.type == ecodes.EV_KEY:
                        key_event = categorize(event)

                        if key_event.scancode in (ecodes.KEY_LEFTMETA, ecodes.KEY_RIGHTMETA): # Super
                            modifs['super'] = False
                            pipe.send(Key(key_event.scancode, key_event.keystate, modifs))
                            modifs['super'] = key_event.keystate != 0 # 1 = Pressed, 0 = Released, 2 = Hold
                        elif key_event.scancode in (ecodes.KEY_LEFTALT, ecodes.KEY_RIGHTALT): # Alt
                            modifs['alt'] = False
                            pipe.send(Key(key_event.scancode, key_event.keystate, modifs))
                            modifs['alt'] = key_event.keystate != 0
                        elif key_event.scancode in (ecodes.KEY_LEFTCTRL, ecodes.KEY_RIGHTCTRL): # Ctrl
                            modifs['ctrl'] = False
                            pipe.send(Key(key_event.scancode, key_event.keystate, modifs))
                            modifs['ctrl'] = key_event.keystate != 0
                        elif key_event.scancode in (ecodes.KEY_LEFTSHIFT, ecodes.KEY_RIGHTSHIFT): # Shift
                            modifs['shift'] = False
                            pipe.send(Key(key_event.scancode, key_event.keystate, modifs))
                            modifs['shift'] = key_event.keystate != 0
                        else:
                            pipe.send(Key(key_event.scancode, key_event.keystate, modifs))
            except KeyboardInterrupt:
                pipe.send(Key(ecodes.KEY_C, 1, modifs))
    
    def handleQueue(self):
        for ev in list(self.events.keys()):
            if self.events[ev].state == 0:
                self.events.pop(ev)
            elif self.events[ev].state == 1:
                self.events[ev].state = 2
        try:
            while self.pipe.poll():
                nev = self.pipe.recv()
                if nev.scancode in self.events and nev == self.events[nev.scancode]:
                    nev.heldFor = self.events[nev.scancode].heldFor + 1
                self.events[nev.scancode] = nev
        except Empty:
            pass
        return list(self.events.values())
