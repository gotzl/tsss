import wavdecode
import glob
import wave
import numpy as np
import cProfile

CHANNELS = 2
SAMPLEWIDTH = 3 # 24bi
SAMPLERATE = 48000
FRAMESPERBUFFER = 48000

wav = wave.open(glob.glob("/home/gotzl/Downloads/2 x 8'/*/*")[0], 'rb')
frame = wav.readframes(FRAMESPERBUFFER)
frames = []
frames = [(frame, np.zeros(0), len(frame), 0)]*10

def f():
    wavdecode.mix(frames,
                  FRAMESPERBUFFER,
                  CHANNELS,
                  SAMPLEWIDTH)

cProfile.run('f()')

