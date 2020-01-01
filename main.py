#!/usr/bin/env python

# TheSuperSimpleSampler
import cProfile
from multiprocessing import Lock
from rtmidi.midiutil import open_midiinput
from rtmidi.midiconstants import NOTE_ON, NOTE_OFF

import matplotlib.pyplot as plt

import sys
import os
import time

sys.path.append('tsss')
import wavdecode


CHANNELS = 2
SAMPLEWIDTH = 3 # 24bit
# SAMPLERATE = 24000
SAMPLERATE = 48000
# SAMPLERATE = 192000
# FRAMESPERBUFFER = 512
FRAMESPERBUFFER = 1024
# FRAMESPERBUFFER = 2048
# FRAMESPERBUFFER = 4096


base = sys.argv[1] if len(sys.argv) > 1 else "/home/gotzl/Downloads/"
port = None  # sys.argv[1] if len(sys.argv) > 1 else None

mutex = Lock()
data = []
chan_map = {}


def getframes(instruments, frame_count):
    frames = []

    for inst in instruments:
        for note in list(inst.playing.values())+list(inst.ending.values()):
            fr, de = note.getframe(frame_count)
            frames.append((fr, de, len(fr), len(de) > 0))

    return frames


def mixer(frame_count):
    global data, chan_map
    mutex.acquire()
    try:
        frames = getframes(chan_map[0], frame_count)
        now = time.time()
        newdata = wavdecode.mix(
            frames,
            frame_count,
            CHANNELS,
            SAMPLEWIDTH)
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
        while True:
            msg = midiin.get_message()

            # delta = time.time() - last
            # if delta > 1 and n<2:
            #     # if n == 0:
            #     last = time.time()
            #     msg = [NOTE_ON if n%2 == 0 else NOTE_OFF, 36 + (n>>1)%50], delta
            #     n += 1
            # elif delta > 1 and n > 1: break

            if msg:
                m, deltatime = msg
                timer += deltatime
                print("[%s] @%0.6f %r" % (port_name, timer, m))

                if m[0] not in [NOTE_ON, NOTE_OFF]: continue
                mutex.acquire()
                try:
                    list(map(lambda x: x.play(m[1], m[0] == NOTE_ON), chan_map[0]))
                finally:
                    mutex.release()

            mutex.acquire()
            try:
                list(map(lambda x:x.cleanup(), chan_map[0]))
            finally:
                mutex.release()

            active = sum(map(lambda x:len(x.playing)+len(x.ending), chan_map[0]))

            if active != last_active:
                print("Active notes %i"%active)
                last_active = active

            time.sleep(0.01)

    try:
        instruments = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]

        print("Found the following instruments:")
        for i, p in enumerate(instruments): print(i, p)

        print("Map instrument to MIDI channel. ")
        while True:
            chan = input("Type channel number, then instrument number, ie '0 1 2 3 4' and hit ENTER (or leave blank and hit ENTER)")
            if len(chan) == 0: break
            sel = chan.split()
            if len(sel) < 2:
                print("Invalid input")
                continue
            sel = list(map(int, sel))
            chan_map[sel[0]] = [instruments[i] for i in sel[1:]]

        if len(chan_map) == 0:
            raise Exception("No instrument selected")

        for c, i in chan_map.items():
            chan_map[c] = list(map(Instrument.Instrument, i))

        print("Starting Audio stream and MIDI input loop")
        stream.start_stream()

        # cProfile.run('eventloop()')
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

