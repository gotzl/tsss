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

fs = sorted(glob.glob("/run/media/gotzl/stuff/realsamples/German Harpsichord 1741/Front 8'/*/*.wav"))
wavs = [wave.open(f, 'rb') for f in fs[:10]]
frame = [w.readframes(FRAMESPERBUFFER*4) for w in wavs]
frames = [(f, np.array([]), len(f), 0, wavs[0].getframerate()/SAMPLERATE) for f in frame]

print(fs[-1])
sample, sr = librosa.load(fs[-1], mono=False, sr=SAMPLERATE, duration=1)
resample = [
    librosa.effects.pitch_shift(
        np.asfortranarray(sample[0]), sr, n_steps=2.),
    librosa.effects.pitch_shift(
        np.asfortranarray(sample[1]), sr, n_steps=2.)
    ]
sample = np.column_stack((sample[0], sample[1])).ravel()
sample *= 0x800000

# resample, sr = sf.read(fs[0])
# resample = resample.T
resample = np.column_stack((resample[0], resample[1])).ravel()
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
    CHUNK = 1024

    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(SAMPLEWIDTH),
                    channels=CHANNELS,
                    rate=SAMPLERATE,
                    output=True)

    note1 = Note.Note(sample, rate=sr, channel=CHANNELS, decay=np.array([]))
    note2 = Note.Note(resample, rate=sr, channel=CHANNELS, decay=np.array([]))

    idx = 0
    while not note1.done() or not note2.done():
        note = note2 if note1.done() else note1

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


    note1.close()
    note2.close()

    stream.stop_stream()
    stream.close()

    p.terminate()

# cProfile.run('f()')
resample_test()
