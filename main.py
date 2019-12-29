#!/usr/bin/env python

# TheSuperSimpleSampler

from rtmidi.midiutil import open_midiinput
from rtmidi.midiconstants import NOTE_ON, NOTE_OFF
import pygame_sdl2
pygame_sdl2.import_as_pygame()
import pygame

import sys
import os
import time
import glob


# pygame.mixer.pre_init(44100, 16, 2, 1024)
pygame.mixer.init(buffer=512)
pygame.mixer.set_num_channels(32)

base = sys.argv[1] if len(sys.argv) > 1 else "/home/gotzl/Downloads/"
port = None  # sys.argv[1] if len(sys.argv) > 1 else None

try:
    midiin, port_name = open_midiinput(port)
except (EOFError, KeyboardInterrupt):
    pygame.mixer.quit()
    sys.exit()

try:
    chan_map = {}

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


    class Instrument(object):
        def __init__(self, name):
            self.name = name
            self.on = {}
            self.off = {}
            self.playing = {}
            self.offset = None
            print("Loading sound for %s"%self.name)
            self.get_sounds()

        def get_sounds(self):
            for f in glob.glob(str(os.path.join(base, self.name) + '/*/*.wav')):
                wav = os.path.split(f)
                if wav[1][0] != '1': continue
                note = os.path.split(wav[0])
                sound = pygame.mixer.Sound(f)

                if 'Release' in f:
                    self.off[int(note[-1][:2])] = sound
                else: self.on[int(note[-1][:2])] = sound
            self.offset = 36 - sorted(self.on.keys())[0]

        def play(self, i, is_on):
            idx = i - self.offset
            notes = self.on if is_on else self.off

            if idx in self.playing:
                self.playing[idx].stop()

            if idx in notes.keys():
                self.playing[idx] = notes[idx]
                self.playing[idx].play()


    if len(chan_map) == 0:
        raise Exception("No instrument selected")

    for c, i in chan_map.items():
        chan_map[c] = list(map(Instrument, i))

    print("Starting input loop")
    timer = time.time()
    while True:
        msg = midiin.get_message()

        if msg:
            m, deltatime = msg
            timer += deltatime
            print("[%s] @%0.6f %r" % (port_name, timer, m))

            if m[0] not in [NOTE_ON, NOTE_OFF]: continue
            list(map(lambda x: x.play(m[1], m[0] == NOTE_ON), chan_map[0]))

        time.sleep(0.001)

except KeyboardInterrupt:
    print('')
finally:
    print("Exit.")
    pygame.mixer.quit()

    midiin.close_port()
    del midiin
