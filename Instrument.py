import glob
import os
import wave
import librosa
import numpy as np

import Note
from main import SAMPLERATE


class Instrument(object):
    def __init__(self, base, name):
        self.base = base
        self.name = name
        self.on = {}
        self.off = {}
        self.playing = {}
        self.ending = {}
        self.active = False
        self.offset = None
        print("Loading samples for %s"%self.name)
        self.get_samples()
        # self.complete_samples(-4, 61)
        self.complete_samples(3, 56)

    def complete_samples(self, low, hi):
        on, off = {}, {}
        for i in range(low, hi+1):
            sr = SAMPLERATE
            if i not in self.on:
                idx = min(self.on, key=lambda x:abs(x-i))
                print('adding note',i,idx, i-idx)
                w = self.on[idx][0]
                on[i] = librosa.effects.pitch_shift(
                    librosa.load(w, sr=sr)[0],
                    sr, n_steps=i-idx)
                print(len(on[i]), on[i].dtype , wave.open(w,'rb').getnframes())

            if i not in self.off:
                idx = min(self.off, key=lambda x:abs(x-i))
                print('adding note',i,idx, i-idx)
                w = self.off[idx][0]
                off[i] = librosa.effects.pitch_shift(
                    librosa.load(w, sr=sr)[0],
                    sr, n_steps=i-idx)

        self.on.update(on)
        self.off.update(off)

    def get_samples(self):
        from main import CHANNELS
        for f in glob.glob(str(os.path.join(self.base, self.name) + '/*/*.wav')):
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
        decay_x = np.linspace(0, decay, int(np.ceil(decay)))
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
            if isinstance(notes[idx], list):
                self.playing[idx] = Note.Note(notes[idx][self.group%len(notes[idx])], decay=self.decay)
                self.group += 1
            else:
                self.playing[idx] = Note.RawNote(notes[idx], decay=self.decay)

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

