import sys

sys.path.append('tsss')
import wavdecode
import glob
import time
import wave
import numpy as np
import cProfile
import librosa

CHANNELS = 2
SAMPLEWIDTH = 3 # 24bi
SAMPLERATE = 48000
FRAMESPERBUFFER = 48000
# FRAMESPERBUFFER = 1024


fs = glob.glob("/home/gotzl/Downloads/2 x 8'/*/*.wav")[:10]
wavs = [wave.open(f, 'rb') for f in fs]
frame = [w.readframes(FRAMESPERBUFFER*4) for w in wavs]
frames = [(f, np.random.uniform(0,1,FRAMESPERBUFFER*4*2), len(f), 1, wavs[0].getframerate()/SAMPLERATE) for f in frame]

resample = librosa.effects.pitch_shift(
    librosa.load(fs[0], sr=SAMPLERATE)[0],
    SAMPLERATE, n_steps=-1.)
frames.append((resample, np.random.uniform(0,1,FRAMESPERBUFFER*4*2), len(resample), 1, 1))

def f():
    now = time.time()
    print(len(wavdecode.mix(frames,
                  FRAMESPERBUFFER,
                  CHANNELS,
                  SAMPLEWIDTH, 1)))
    print(time.time() - now)

cProfile.run('f()')

