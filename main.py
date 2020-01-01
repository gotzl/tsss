#!/usr/bin/env python

# TheSuperSimpleSampler
import threading
from multiprocessing import Lock
from rtmidi.midiutil import open_midiinput
from rtmidi.midiconstants import NOTE_ON, NOTE_OFF
# import pygame_sdl2
# pygame_sdl2.import_as_pygame()
# import pygame

import pyaudio
import wave
import copy
import numpy as np
# import scipy.signal as sps
import matplotlib.pyplot as plt

import sys
import os
import struct
import time
import glob

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

# pygame.mixer.init(buffer=512)
# pygame.mixer.set_num_channels(32)

base = sys.argv[1] if len(sys.argv) > 1 else "/home/gotzl/Downloads/"
port = None  # sys.argv[1] if len(sys.argv) > 1 else None

try:
    midiin, port_name = open_midiinput(port)
except (EOFError, KeyboardInterrupt):
    # pygame.mixer.quit()
    sys.exit()


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


def mixer():
    global data, chan_map

    frames = getframes(chan_map[0], FRAMESPERBUFFER)

    now = time.time()

    newdata = wavdecode.mix(
        frames,
        FRAMESPERBUFFER,
        CHANNELS,
        SAMPLEWIDTH)
    print(time.time()-now)

    mutex.acquire()
    try:
        data = bytes(newdata)
    finally:
        mutex.release()


def callback(in_data, frame_count, time_info, status):
    # dd = mix(frame_count)
    global data
    mutex.acquire()
    try:
        dd = copy.copy(data)
        data = []
    finally:
        mutex.release()

    if dd is None or len(dd) == 0:
        dd = np.zeros(frame_count * CHANNELS * SAMPLEWIDTH, dtype=np.int8)

    return (dd, pyaudio.paContinue)


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


    class Note(object):
        def __init__(self, path, decay):
            print("Starting note %s"%os.path.split(path)[1], self)
            self.wav = wave.open(path, 'rb')
            self.decay = decay
            self.decay_pos = -1
            self.factor = int(self.wav.getframerate()/SAMPLERATE)

        def done(self):
            return self.decay_pos >= len(self.decay) or self.wav.tell() == self.wav.getnframes()

        def close(self):
            print("Closing note.", self)
            self.wav.close()

        def end(self):
            print("Ending note.", self)
            self.decay_pos = 0

        def getframe(self, frame_count):
            # read frames from the wave
            _bytes = self.wav.readframes(frame_count * self.factor)

            # create decay values
            decay = np.array([])
            if self.decay_pos >= 0:
                self.decay_pos += int(len(_bytes)/3)
                decay = self.decay[self.decay_pos:self.decay_pos+int(len(_bytes)/3)]
                decay = np.pad(decay, [(0, int(len(_bytes)/3) - len(decay))], mode='constant')
            return _bytes, decay


    class Instrument(object):
        def __init__(self, name):
            self.name = name
            self.on = {}
            self.off = {}
            self.playing = {}
            self.ending = {}
            self.offset = None
            print("Loading samples of %s"%self.name)
            self.get_samples()

        def get_samples(self):
            for f in glob.glob(str(os.path.join(base, self.name) + '/*/*.wav')):
                wav = os.path.split(f)
                note = os.path.split(wav[0])
                # sound = pygame.mixer.Sound(f)
                notes = self.off if 'Release' in f else self.on
                idx = int(note[-1][:2])
                if idx not in notes: notes[idx] = []
                notes[idx].append(f)
                notes[idx] = sorted(notes[idx])

            self.offset = 36 - sorted(self.on.keys())[0]
            self.group = 0

            # calculate the decay factor
            wav = wave.open(list(self.on.values())[0][0], 'rb')
            decay = .6 * wav.getframerate()
            decay_x = np.linspace(0, decay, np.ceil(decay))
            decay_fac = np.array(list(map(lambda x: np.exp(-x/(decay/4)), decay_x))).clip(min=0)

            # plt.plot(decay_x,decay_fac)
            # plt.show()

            self.decay = np.empty((CHANNELS*decay_fac.size,), dtype=decay_fac.dtype)
            for i in range(CHANNELS):
                self.decay[i::CHANNELS] = decay_fac
            wav.close()

        def play(self, i, is_on):
            idx = i - self.offset
            notes = self.on if is_on else self.off

            if idx in self.playing:
                if idx in self.ending:
                    self.ending[idx].close()
                    del self.ending[idx]
                self.ending[idx] = self.playing[idx]
                self.ending[idx].end()
                del self.playing[idx]

            if idx in notes.keys():
                self.playing[idx] = Note(notes[idx][self.group%len(notes[idx])], decay=self.decay)
                self.group += 1

        def cleanup(self):
            # frames = list(map(lambda x: x.getframe(frame_count), list(self.playing.values())+list(self.ending.values())))
            remove = [idx for idx in self.playing if self.playing[idx].done()]
            for idx in remove:
                self.playing[idx].close()
                del self.playing[idx]

            remove = [idx for idx in self.ending if self.ending[idx].done()]
            for idx in remove:
                self.ending[idx].close()
                del self.ending[idx]


    if len(chan_map) == 0:
        raise Exception("No instrument selected")

    for c, i in chan_map.items():
        chan_map[c] = list(map(Instrument, i))

    print("Starting Audio stream and MIDI input loop")
    stream.start_stream()

    timer = time.time()
    last = time.time()
    last_active = 0
    n = 0
    while True:
        msg = midiin.get_message()

        delta = time.time() - last
        if delta > 1 and n<2:
        # if n == 0:
           last = time.time()
           msg = [NOTE_ON if n%2 == 0 else NOTE_OFF, 36 + (n>>1)%50], delta
           n += 1

        if msg:
            m, deltatime = msg
            timer += deltatime
            print("[%s] @%0.6f %r" % (port_name, timer, m))

            if m[0] not in [NOTE_ON, NOTE_OFF]: continue
            # mutex.acquire()
            # try:
            list(map(lambda x: x.play(m[1], m[0] == NOTE_ON), chan_map[0]))
            # finally:
            #     mutex.release()

        if len(data) == 0:
            mixer()

        list(map(lambda x:x.cleanup(), chan_map[0]))
        active = sum(map(lambda x:len(x.playing)+len(x.ending), chan_map[0]))

        if active != last_active:
            print("Active notes %i"%active)
            last_active = active

        time.sleep(0.001)

except KeyboardInterrupt:
    print('')
finally:
    print("Exit.")

    stream.stop_stream()
    stream.close()
    p.terminate()

    midiin.close_port()
    del midiin
