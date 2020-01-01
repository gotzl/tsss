import os
import wave
import numpy as np


class Note(object):
    def __init__(self, path, decay):
        from main import SAMPLERATE
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
