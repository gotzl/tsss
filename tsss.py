import time

from rtmidi.midiconstants import NOTE_ON, NOTE_OFF


def getframes(instruments, frame_count):
    frames = []

    for inst in instruments:
        for note in list(inst.playing.values())+list(inst.ending.values()):
            fr, de = note.getframe(frame_count)
            frames.append((fr, de, len(fr), len(de) > 0, note.factor))

    return frames


class MidiInputHandler(object):
    def __init__(self, port, registers, mutex):
        self.port = port
        self.registers = registers
        self.mutex = mutex
        self.offset = False
        self._wallclock = time.time()

    def __call__(self, event, data=None):
        message, deltatime = event
        self._wallclock += deltatime
        print("[%s] @%0.6f %r" % (self.port, self._wallclock, message))

        cmd = message[0]&0xfff0
        chan = message[0]&0xf

        if cmd in [NOTE_ON, NOTE_OFF]:
            # some send NOTE_ON with velocity=0 instead of NOTE_OFF
            if message[2] == 0 and cmd == NOTE_ON: cmd = NOTE_OFF

            self.mutex.acquire()
            try:
                for key, reg in self.registers.items():
                    if key[0] == chan and reg.active:
                        reg.play(message[1] + (2 if self.offset else 0), cmd == NOTE_ON)
            finally:
                self.mutex.release()

        else:
            # enable/disable registers
            for key, reg in self.registers.items():
                if key[1] == (message[0], message[1]):
                    reg.active = not reg.active
                    print('%s register \'%s\''%('Enabling' if reg.active else 'Disabling', reg.name))

            if message[0] == 0xCB:
                # enable/disable offset from 399Hz -> 440Hz
                if message[1] == 25:
                    self.offset = not self.offset
                    print('%s register offset'%('Enabling' if self.offset else 'Disabling'))


def loop(registers, mutex, midihandler):
    from main import DEBUG

    n = 0
    last_active = 0
    last = time.time()

    while True:
        delta = time.time() - last
        # if delta > 1 and n<2:
        # if n == 0:
        if DEBUG and delta > 1:
            last = time.time()
            _min = min(registers[0, (203, 0)].on)
            _max = max(registers[0, (203, 0)].on)
            msg = [NOTE_ON if n%2 == 0 else NOTE_OFF,
                   _min + (n>>1)%(_max-_min),
                   50], delta
            midihandler.__call__(msg)
            n += 1

        mutex.acquire()
        try:
            list(map(lambda x:x.cleanup(), registers.values()))
        finally:
            mutex.release()

        active = sum(map(lambda x:len(x.playing)+len(x.ending), registers.values()))

        if active != last_active:
            print("Active notes %i"%active)
            last_active = active

        time.sleep(0.1)