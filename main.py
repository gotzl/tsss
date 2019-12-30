#!/usr/bin/env python

# TheSuperSimpleSampler
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

import sys
import os
import struct
import time
import glob

CHANNELS = 2
SAMPLEWIDTH = 3 # 24bit
SAMPLERATE = 48000
# SAMPLERATE = 192000
FRAMESPERBUFFER = 512

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

def mix(frame_count):
    # global data
    frames = []
    for instruments in chan_map.values():
        for i in instruments:
            if len(i.playing) > 0:
                # mutex.acquire()
                # try:
                frames.append(i.mix(frame_count))
                # finally:
                #     mutex.release()

    if len(frames) == 0:
        return

    # mix instruments together
    dd = np.sum(frames, axis=0, dtype=np.int32)
    # dd = np.mean(frames, axis=0, dtype=np.int32)
    return dd


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
stream = p.open(format=p.get_format_from_width(SAMPLEWIDTH),
                channels=CHANNELS,
                rate=SAMPLERATE,
                frames_per_buffer=FRAMESPERBUFFER,
                start=False,
                output=True,
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
        def __init__(self, path):
            self.wav = wave.open(path, 'rb')
            self.decay = .1 * self.wav.getframerate()
            self.factor = int(self.wav.getframerate()/SAMPLERATE)
            self.decay_pos = -1

        def done(self):
            return self.decay_pos >= self.decay or self.wav.tell() == self.wav.getnframes()

        def close(self):
            self.wav.close()

        def end(self):
            self.decay_pos = 0

        def getframe(self, frame_count):
            # read frames from the wave
            # data = np.frombuffer(self.wav.readframes(frame_count * self.factor), np.uint8)
            bytes = self.wav.readframes(frame_count * self.factor)

            # apply decay
            if self.decay_pos >= 0:
                data = []
                for i in range(0, len(bytes), 3):
                    b = bytearray([0]) + bytes[i:i+3]
                    data.append(struct.unpack('I', b)[0] >> 8)
                data = np.array(data, dtype=np.float)

                # create x values for decay calculation
                xi = np.linspace(self.decay_pos, self.decay_pos + frame_count * self.factor, int(len(data)/CHANNELS))
                decayi = np.array(list(map(lambda x: x/self.decay, xi))).clip(min=0)
                decay = np.empty((CHANNELS*xi.size,), dtype=xi.dtype)
                decay[0::2] = decayi
                decay[1::2] = decayi
                # get and apply decay factor
                data = (decay * data).astype(np.int32)
                self.decay_pos += frame_count * self.factor

            else:
                # FIXME: this does not work!
                # get individual samples (24bit, little endian)
                data = np.frombuffer(bytes, 'V3').astype('V4').view(np.int32)

            # add silence if not enough frames
            data = np.pad(data, [(0, frame_count * self.factor * CHANNELS - len(data))], mode='constant')

            if self.wav.getframerate() == SAMPLERATE:
                return data

            # # downsample to the output rate
            # l = sps.resample(data[0::2], frame_count).astype(np.int32)
            # r = sps.resample(data[1::2], frame_count).astype(np.int32)
            # # put left and right channel back together again
            # c = np.empty((l.size + r.size,), dtype=l.dtype)
            # c[0::2] = l
            # c[1::2] = r
            # return np.array(c)

            return data[::self.factor]


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
                notes = self.off  if 'Release' in f else self.on
                idx = int(note[-1][:2])
                if idx not in notes: notes[idx] = []
                notes[idx].append(f)
                notes[idx] = sorted(notes[idx])

            self.offset = 36 - sorted(self.on.keys())[0]
            self.group = 0

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
                self.playing[idx] = Note(notes[idx][self.group%len(notes[idx])])
                self.group += 1

        def mix(self, frame_count):
            frames = list(map(lambda x: x.getframe(frame_count), list(self.playing.values())+list(self.ending.values())))
            remove = [idx for idx in self.playing if self.playing[idx].done()]
            for idx in remove:
                self.playing[idx].close()
                del self.playing[idx]

            remove = [idx for idx in self.ending if self.ending[idx].done()]
            for idx in remove:
                self.ending[idx].close()
                del self.ending[idx]

            return np.sum(frames, axis=0, dtype=np.int32)
            # return np.mean(frames, axis=0, dtype=np.int32)


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

        # delta = time.time() - last
        # if delta > .5:
        #    last = time.time()
        #    msg = [NOTE_ON, 36 + n%50], delta
        #    n += 1

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

        active = sum(map(lambda x:len(x.playing)+len(x.ending), chan_map[0]))

        if active>0 and data is not None and len(data)==0:
            newdata = mix(FRAMESPERBUFFER)

            _data = bytearray()
            for i in newdata:
                _data += bytearray(struct.pack('I',(i&0x00ffffff)<<8)[1:])

            # print(len(newdata),len(_data))

            mutex.acquire()
            try:
                data = bytes(_data)
            finally:
                mutex.release()

        if active != last_active:
            print("Active notes %i"%active)
            last_active = active

        time.sleep(0.001)

except KeyboardInterrupt:
    print('')
finally:
    print("Exit.")
    # pygame.mixer.quit()

    stream.stop_stream()
    stream.close()
    p.terminate()

    midiin.close_port()
    del midiin
