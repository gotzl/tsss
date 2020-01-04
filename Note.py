import wave
import os
import numpy as np

from main import DEBUG, SAMPLERATE


class Note(object):
    def __init__(self, data, rate, channel, decay):
        if DEBUG: print("Starting note", self)
        self.pos = 1
        self.data = data
        self.decay = decay
        self.decay_pos = -1
        self.factor = int(np.ceil(rate/SAMPLERATE))
        self.channel = channel

    def done(self):
        return self.decay_pos >= len(self.decay) or self.pos >= len(self.data)

    def close(self):
        if DEBUG: print("Closing note.", self)

    def end(self):
        if DEBUG: print("Ending note.", self)
        self.decay_pos = 0

    def getdecay(self, frame_count):
        # create decay values
        decay = np.array([], dtype=self.decay.dtype)
        if self.decay_pos >= 0:
            decay = self.decay[self.decay_pos:self.decay_pos + 2*frame_count]
            decay = np.pad(decay, [(0, 2*frame_count - len(decay))], mode='constant')
            self.decay_pos += 2*frame_count
        return decay

    def getframe(self, frame_count):
        # read frames from the wave
        m = frame_count * self.channel * self.factor
        _data = self.data[self.pos:min(len(self.data), self.pos + m)]
        self.pos += m
        return _data, self.getdecay(frame_count)


class WavNote(Note):
    def __init__(self, path, decay):
        self.wav = wave.open(path, 'rb')
        super().__init__(None, self.wav.getframerate(), self.wav.getnchannels(), decay)
        if DEBUG: print("Wave %s"%os.path.split(path)[1], self)

    def done(self):
        return self.decay_pos >= len(self.decay) or self.wav.tell() == self.wav.getnframes()

    def close(self):
        super().close()
        self.wav.close()

    def getframe(self, frame_count):
        # read frames from the wave, its in bytes, so be aware of 16/24 bitnes...
        _bytes = self.wav.readframes(frame_count * self.factor)
        return _bytes, self.getdecay(frame_count)
