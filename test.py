import sys

sys.path.append('tsss')
import wavdecode
import Note

import pyaudio
import glob
import time
import wave
import numpy as np
import cProfile
import librosa
import soundfile as sf

CHANNELS = 2
SAMPLEWIDTH = 3 # 24bi
SAMPLERATE = 48000
FRAMESPERBUFFER = 48000
# FRAMESPERBUFFER = 1024

fs = glob.glob("/run/media/gotzl/stuff/realsamples/German Harpsichord 1741/2 x 8'/*/*.wav")[:10]
wavs = [wave.open(f, 'rb') for f in fs]
frame = [w.readframes(FRAMESPERBUFFER*4) for w in wavs]
frames = [(f, np.array([]), len(f), 0, wavs[0].getframerate()/SAMPLERATE) for f in frame]

resample, sr = librosa.load(fs[0], mono=False, sr=None)
resample = [
    librosa.effects.pitch_shift(
        np.asfortranarray(resample[0]), sr, n_steps=-1.),
    librosa.effects.pitch_shift(
        np.asfortranarray(resample[1]), sr, n_steps=-1.)
    ]

# resample, sr = sf.read(fs[0])
# resample = resample.T
print(resample[:10])
resample = np.column_stack((resample[0], resample[1])).ravel()
print(resample[:10])
resample *= 0x800000
frames.append((resample, np.array([]), len(resample), 0, sr/SAMPLERATE))


def f():
    now = time.time()
    print(len(wavdecode.mix(frames,
                  FRAMESPERBUFFER,
                  CHANNELS,
                  SAMPLEWIDTH, 1)))
    print(time.time() - now)


def resample_test():
    CHUNK = 16

    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(SAMPLEWIDTH),
                    channels=CHANNELS,
                    rate=SAMPLERATE,
                    output=True)

    note = Note.Note(resample, rate=sr, channel=CHANNELS, decay=np.array([]))

    idx = 0
    while not note.done():
        fr, de = note.getframe(CHUNK)
        frames = [(fr*0x100, de, len(fr), len(de) > 0, note.factor)]

        d = wavdecode.mix(
            frames,
            CHUNK,
            CHANNELS,
            SAMPLEWIDTH, 0)

        # print(fr[::4]*0x100)
        # print((fr[::4]/0x100).astype('<i2').tobytes())
        # print(bytes(d))
        # print(len(d), len((fr[::4]/0x100).astype('<i2').tobytes()))

        # works when using 16bit sample rate
        # stream.write((fr[::4]/0x100).astype('<i2').tobytes())

        stream.write(d)
        idx += CHUNK


    note.close()

    stream.stop_stream()
    stream.close()

    p.terminate()

# cProfile.run('f()')
resample_test()
