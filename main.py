#!/usr/bin/env python

# TheSuperSimpleSampler
from multiprocessing import Lock
from rtmidi.midiutil import open_midiinput
from rtmidi.midiconstants import NOTE_ON, NOTE_OFF
# import matplotlib.pyplot as plt

import sys
import time

sys.path.append('tsss')
import wavdecode

DEBUG = False

CHANNELS = 2
SAMPLEWIDTH = 3 # 24bit
# SAMPLERATE = 24000
# SAMPLERATE = 41000
SAMPLERATE = 48000
# SAMPLERATE = 192000
# FRAMESPERBUFFER = 256
FRAMESPERBUFFER = 512
# FRAMESPERBUFFER = 1024
# FRAMESPERBUFFER = 2048
# FRAMESPERBUFFER = 4096


base = sys.argv[1] if len(sys.argv) > 1 else "/home/gotzl/Downloads/"
port = None  # sys.argv[1] if len(sys.argv) > 1 else None

mutex = Lock()
data = []
registers = {}


def getframes(instruments, frame_count):
    frames = []

    for inst in instruments:
        for note in list(inst.playing.values())+list(inst.ending.values()):
            fr, de = note.getframe(frame_count)
            frames.append((fr, de, len(fr), len(de) > 0, note.factor))

    return frames


def mixer(frame_count):
    global data, registers
    mutex.acquire()
    try:
        frames = getframes(registers.values(), frame_count)
        now = time.time()
        newdata = wavdecode.mix(
            frames,
            frame_count,
            CHANNELS,
            SAMPLEWIDTH, 0)
        # print(len(frames), len(newdata),time.time() - now)
    finally:
        mutex.release()
    return bytes(newdata)


def callback(in_data, frame_count, time_info, status):
    dd = mixer(frame_count)
    return (dd, pyaudio.paContinue)


if __name__ == '__main__':
    import Instrument
    import pyaudio
    import yaml
    import signal

    stop = False
    def signal_handler(sig, frame):
        global stop
        stop = True
    signal.signal(signal.SIGINT, signal_handler)

    try:
        midiin, port_name = open_midiinput(port)
    except (EOFError, KeyboardInterrupt):
        sys.exit()

    p = pyaudio.PyAudio()

    outdev = None
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
            print("Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))
            if (p.get_device_info_by_host_api_device_index(0, i).get('name') == 'pulse'):
                outdev = i

    stream = p.open(
        format=p.get_format_from_width(SAMPLEWIDTH),
        channels=CHANNELS,
        rate=SAMPLERATE,
        frames_per_buffer=FRAMESPERBUFFER,
        start=False,
        output=True,
        output_device_index=outdev,
        stream_callback=callback)

    def eventloop():
        timer = time.time()
        last = time.time()
        last_active = 0
        n = 0
        offset = False

        if DEBUG:
            registers[0, (203, 0)].active = True


        while not stop:
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

    try:
        now = time.time()
        instruments = yaml.safe_load(open('instruments.yaml'))

        for name, inst in instruments.items():
            print('Opening %s'%name)
            for n, ch in inst['channel'].items():
                for reg, regname in ch['registers'].items():
                    try:
                        registers[n, tuple(map(int, reg.split()))] = Instrument.Instrument(
                            inst['path'],
                            inst['lowest'],
                            regname,
                            ch['keys']
                        )
                    except Exception as e:
                        print("Unable to open %s"%regname)
                        print(e)

        print("Loading of instruments took %.2f seconds"%(time.time()-now))
        print("Starting Audio stream and MIDI input loop. You may start hitting the keys!")
        stream.start_stream()

        eventloop()

    except KeyboardInterrupt:
        print('')
    finally:
        print("Exit.")

        stream.stop_stream()
        stream.close()
        p.terminate()

        midiin.close_port()
        del midiin

