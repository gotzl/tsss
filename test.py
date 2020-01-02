import sys

sys.path.append('tsss')
import wavdecode
import glob
import time
import wave
import numpy as np
import cProfile

CHANNELS = 2
SAMPLEWIDTH = 3 # 24bi
SAMPLERATE = 48000
FRAMESPERBUFFER = 48000
# FRAMESPERBUFFER = 1024


wavs = [wave.open(f, 'rb') for f in glob.glob("/home/gotzl/Downloads/2 x 8'/*/*.wav")[:10]]
frame = [w.readframes(FRAMESPERBUFFER*4) for w in wavs]
frames = [(f, np.random.uniform(0,1,FRAMESPERBUFFER*4*2), len(f), 1, wavs[0].getframerate()/SAMPLERATE) for f in frame]


def f():
    now = time.time()
    print(len(wavdecode.mix(frames,
                  FRAMESPERBUFFER,
                  CHANNELS,
                  SAMPLEWIDTH, 1)))
    print(time.time() - now)

cProfile.run('f()')

