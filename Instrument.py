import glob
import os
import wave
from multiprocessing.pool import ThreadPool

import librosa
import numpy as np

import Note

library = {}


class Instrument(object):
    def __init__(self, base, lowest, name, keys):
        self.base = base
        self.name = name
        self.on = {}
        self.off = {}
        self.playing = {}
        self.ending = {}
        self.active = False
        self.group = 0
        self.decay = None
        print("Loading samples for %s"%self.name)
        self.get_samples(lowest)
        self.complete_samples(*keys)

    def create_sample(self, target, is_on):
        from main import SAMPLERATE
        notes = self.on if is_on else self.off
        source = min(notes, key=lambda x: abs(x - target))
        w = notes[source][0]
        id = "%s_%i"%(w, target)
        if id not in library:
            print('Creating note from %s, %i steps (%i %i)'%(os.path.split(w)[1], target-source, target, source))
            data, sr = librosa.load(w, mono=False, sr=SAMPLERATE)
            l = librosa.effects.pitch_shift(
                np.asfortranarray(data[0]),
                sr, n_steps=target-source)
            r = librosa.effects.pitch_shift(
                np.asfortranarray(data[1]),
                sr, n_steps=target-source)
            library[id] = np.column_stack((l, r)).ravel()*0x80000000, sr, 2
        return target, library[id]

    def complete_samples(self, low, hi):
        pool = ThreadPool(4)
        on = pool.map(lambda i: self.create_sample(i, True),
                      [i for i in range(low, hi+1) if i not in self.on])
        off = pool.map(lambda i: self.create_sample(i, False),
                       [i for i in range(low, hi+1) if i not in self.off])
        pool.close()
        pool.join()

        self.on.update({i:j for i,j in on})
        self.off.update({i:j for i,j in off})

    def get_samples(self, lowest):
        from main import CHANNELS, SAMPLERATE
        offset = None
        for f in sorted(glob.glob(str(os.path.join(self.base, self.name) + '/*/*.wav'))):
            wav = os.path.split(f)
            note = os.path.split(wav[0])
            # sound = pygame.mixer.Sound(f)
            notes = self.off if 'Release' in f else self.on

            i = int(note[-1][:2])
            if offset is None:
                offset = i

            idx = lowest + i - offset
            if idx not in notes: notes[idx] = []

            notes[idx].append(f)
            notes[idx] = sorted(notes[idx])

        # calculate the decay factor
        decay = .6 * SAMPLERATE
        decay_x = np.linspace(0, decay, int(np.ceil(decay)))
        decay_fac = np.array(list(map(lambda x: np.exp(-x/(decay/4)), decay_x))).clip(min=0)

        # plt.plot(decay_x,decay_fac)
        # plt.show()

        self.decay = np.empty((CHANNELS*decay_fac.size,), dtype=decay_fac.dtype)
        for i in range(CHANNELS):
            self.decay[i::CHANNELS] = decay_fac

    def play(self, idx, is_on):
        notes = self.on if is_on else self.off

        if idx in self.playing:
            if idx in self.ending:
                self.ending[idx].close()
                del self.ending[idx]
            self.ending[idx] = self.playing[idx]
            self.ending[idx].end()
            del self.playing[idx]

        if idx in notes.keys():
            if isinstance(notes[idx], list):
                self.playing[idx] = Note.WavNote(notes[idx][self.group%len(notes[idx])], decay=self.decay)
                self.group += 1
            else:
                self.playing[idx] = Note.Note(notes[idx][0], notes[idx][1], notes[idx][2], decay=self.decay)

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
