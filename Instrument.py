import glob
import os
import sys
import wave
import multiprocessing
from multiprocessing.pool import ThreadPool

import numpy as np

sys.path.append('tsss')
import wavdecode
import Note

library = {}


class Instrument(object):
    def __init__(self, base, lowest, name, keys, out_samplerate, out_channels):
        self.base = base
        self.name = name
        self.out_samplerate = out_samplerate
        self.out_channels = out_channels
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
        notes = self.on if is_on else self.off

        source = min(notes, key=lambda x: abs(x - target))
        # source = target - 13 if target > max(notes) else target + 13
        w = notes[source][0]

        id = "%s_%i"%(w, target)
        if id not in library:
            print('Creating note from %s, %i steps (%i %i)'%(os.path.split(w)[1], target-source, target, source))

            w = wave.open(w, 'rb')

            _bytes = w.readframes(w.getnframes())
            if w.getsampwidth() == 3:
                da = np.array(wavdecode.from24le(_bytes))
            elif w.getsampwidth() == 2:
                da = np.frombuffer(_bytes, dtype='<i2')
            elif w.getsampwidth() == 1:
                da = np.frombuffer(_bytes, dtype='<i1')
            else:
                return None

            da = da.astype(np.float32)
            ns = wavdecode.pitchshift(
                da,
                w.getframerate(),
                target-source,
                w.getframerate()//self.out_samplerate)

            # store the data together with sample rate and nchannels
            library[id] = [ns, self.out_samplerate, self.out_channels]

        return target, library[id]

    def complete_samples(self, low, hi):
        pool = ThreadPool(multiprocessing.cpu_count())
        on = pool.starmap(
            self.create_sample,
            [(i, True) for i in range(low, hi+1) if i not in self.on])
        off = pool.starmap(
            self.create_sample,
            [(i, False) for i in range(low, hi+1) if i not in self.off])

        pool.close()
        pool.join()

        self.on.update({i:j for i,j in on})
        self.off.update({i:j for i,j in off})

    def get_samples(self, lowest):
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
        decay = .6 * self.out_samplerate
        decay_x = np.linspace(0, decay, int(np.ceil(decay)))
        decay_fac = np.array(list(map(lambda x: np.exp(-x/(decay/4)), decay_x))).clip(min=0)

        # plt.plot(decay_x,decay_fac)
        # plt.show()

        self.decay = np.empty((self.out_channels*decay_fac.size,), dtype=decay_fac.dtype)
        for i in range(self.out_channels):
            self.decay[i::self.out_channels] = decay_fac
        self.decay = self.decay.astype(np.float32)

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
            if isinstance(notes[idx][0], str):
                self.playing[idx] = Note.WavNote(notes[idx][self.group%len(notes[idx])], decay=self.decay, out_samplerate=self.out_samplerate)
                self.group += 1
            else:
                self.playing[idx] = Note.Note(*notes[idx], decay=self.decay, out_samplerate=self.out_samplerate)

    def cleanup(self):
        for l in [self.playing, self.ending]:
            for idx in [idx for idx in l if l[idx].done()]:
                l[idx].close()
                del l[idx]
