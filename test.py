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


def mix_test():
    wavs = [wave.open(f, 'rb') for f in fs[:10]]
    m = wavs[0].getframerate()//SAMPLERATE
    frame = [w.readframes(FRAMESPERBUFFER*m) for w in wavs]
    frames = [(f, np.array([], dtype=np.float32), len(f), 0, m) for f in frame]
    _bytes = wavdecode.mix(frames,
                            FRAMESPERBUFFER,
                            CHANNELS,
                            SAMPLEWIDTH, 1)
    print(np.array(_bytes)[:20])


def librosa_mix_test():
    sr = librosa.get_samplerate(fs[0])
    m = sr//SAMPLERATE

    frame_length = FRAMESPERBUFFER*m
    hop_length = FRAMESPERBUFFER*m

    strms = map(lambda f:librosa.stream(f,
                            mono=False,
                            fill_value=0.,
                            block_length=1,
                            frame_length=frame_length,
                            hop_length=hop_length), fs)

    frame = [np.zeros(FRAMESPERBUFFER), np.zeros(FRAMESPERBUFFER)]
    for s in strms:
        blk = next(s)
        frame[0] += blk[0][::4]
        frame[1] += blk[1][::4]

    frame = np.column_stack((frame[0], frame[1])).ravel()
    frame *= 0x800000*0x100
    frame /= 4
    data = frame.astype(np.int32)
    _bytes = wavdecode.to24le(data)
    print(np.array(_bytes)[:20])



# # cProfile.run('f()')
# # resample_test()
# mix_test()
# librosa_mix_test()
cProfile.run('mix_test()')
# cProfile.run('librosa_mix_test()')