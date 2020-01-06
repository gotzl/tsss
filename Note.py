import wave
import os
import numpy as np

from main import DEBUG


class Note(object):
    def __init__(self, data, rate, channel, decay, out_samplerate):
        if DEBUG: print("Starting note", self)
        self.pos = 1
        self.data = data
        self.decay = decay
        self.decay_pos = -1

        if rate % out_samplerate != 0:
            raise Exception("The sample frequency of '%i' is not an even multiple of the output sample rate '%i."%(rate, out_samplerate))

        self.factor = rate//out_samplerate
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
    def __init__(self, path, decay, out_samplerate):
        self.wav = wave.open(path, 'rb')
        self.width = self.wav.getsampwidth()
        super().__init__(None, self.wav.getframerate(), self.wav.getnchannels(), decay, out_samplerate)
        if DEBUG: print("Wave %s"%os.path.split(path)[1], self)

    def done(self):
        return self.decay_pos >= len(self.decay) or self.wav.tell() == self.wav.getnframes()

    def close(self):
        super().close()
        self.wav.close()

    def getframe(self, frame_count):
        # read frames from the wave
        _bytes = self.wav.readframes(frame_count * self.factor)

        # 24bit data can not be interpreted easily... just return bytes and take care of of decoding when mixing
        if self.width == 3:
            return _bytes, self.getdecay(frame_count)
        if self.width == 2:
            data = np.frombuffer(_bytes, dtype='<i2')
        elif self.width == 1:
            data = np.frombuffer(_bytes, dtype='<i1')
        else:
            return None

        # the mixing code expects floats
        return data.astype(np.float32), self.getdecay(frame_count)

