import glob
import os
import wave
import numpy as np

import Note


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
        from main import CHANNELS, base
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
            self.playing[idx] = Note.Note(notes[idx][self.group%len(notes[idx])], decay=self.decay)
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

