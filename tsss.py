import time

from rtmidi.midiconstants import NOTE_ON, NOTE_OFF


def getframes(instruments, frame_count):
    frames = []

    for inst in instruments:
        for note in list(inst.playing.values())+list(inst.ending.values()):
            fr, de = note.getframe(frame_count)
            frames.append((fr, de, len(fr), len(de) > 0, note.factor))

    return frames


def eventloop(midiin, port_name, registers, mutex):
    from main import DEBUG

    timer = time.time()
    last = time.time()
    last_active = 0
    n = 0
    offset = False

    while True:
        msg = midiin.get_message()

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
            n += 1

        if msg:
            m, deltatime = msg
            timer += deltatime
            print("[%s] @%0.6f %r" % (port_name, timer, m))
            eventhandler(m, registers, offset, mutex)

        mutex.acquire()
        try:
            list(map(lambda x:x.cleanup(), registers.values()))
        finally:
            mutex.release()

        active = sum(map(lambda x:len(x.playing)+len(x.ending), registers.values()))

        if active != last_active:
            print("Active notes %i"%active)
            last_active = active

        time.sleep(0.001)


def eventhandler(m, registers, offset, mutex):
    cmd = m[0]&0xfff0
    chan = m[0]&0xf

    if cmd in [NOTE_ON, NOTE_OFF]:
        # some send NOTE_ON with velocity=0 instead of NOTE_OFF
        if m[2] == 0 and cmd == NOTE_ON: cmd = NOTE_OFF

        mutex.acquire()
        try:
            for key, reg in registers.items():
                if key[0] == chan and reg.active:
                    reg.play(m[1] + (2 if offset else 0), cmd == NOTE_ON)
        finally:
            mutex.release()

    else:
        # enable/disable registers
        for key, reg in registers.items():
            if key[1] == (m[0], m[1]):
                reg.active = not reg.active
                print('%s register \'%s\''%('Enabling' if reg.active else 'Disabling', reg.name))

        if m[0] == 0xCB:
            # enable/disable offset from 399Hz -> 440Hz
            if m[1] == 25:
                offset = not offset
                print('%s register offset'%('Enabling' if offset else 'Disabling'))

