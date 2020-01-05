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
import pyfftw
librosa.set_fftlib(pyfftw.interfaces.numpy_fft)
import soundfile as sf
from pydub import AudioSegment
from pydub.playback import play

CHANNELS = 2
SAMPLEWIDTH = 3 # 24bi
SAMPLERATE = 48000
FRAMESPERBUFFER = 48000
# FRAMESPERBUFFER = 1024

fs = sorted(glob.glob("/run/media/gotzl/stuff/realsamples/German Harpsichord 1741/Front 8'/*/*.wav"))
wavs = [wave.open(f, 'rb') for f in fs[:10]]
print(fs[-1])

# calculate the decay factor
decay = .6 * SAMPLERATE
decay_x = np.linspace(0, decay, int(np.ceil(decay)))
decay_fac = np.array(list(map(lambda x: np.exp(-x/(decay/4)), decay_x))).clip(min=0)

# plt.plot(decay_x,decay_fac)
# plt.show()

decay = np.empty((CHANNELS*decay_fac.size,), dtype=decay_fac.dtype)
for i in range(CHANNELS):
    decay[i::CHANNELS] = decay_fac
decay = decay.astype(np.float32)


def player(notes):
    CHUNK = 512

    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(SAMPLEWIDTH),
                    channels=CHANNELS,
                    output_device_index=11,
                    rate=SAMPLERATE,
                    output=True)

    while True:
        note = next( (x for x in notes if not x.done()), None)
        if note is None: break

        fr, de = note.getframe(CHUNK)
        frames = [(fr, de, len(fr), len(de) > 0, note.factor)]

        d = wavdecode.mix(
            frames,
            CHUNK,
            CHANNELS,
            SAMPLEWIDTH, 0)

        stream.write(d)

    map(Note.Note.close, notes)

    stream.stop_stream()
    stream.close()

    p.terminate()


def resample_test():
    w = wave.open(fs[-1], 'rb')
    da = np.array(wavdecode.from24le(w.readframes(w.getframerate()))).astype(np.float32)

    shift = 100
    left, right = da[0::2], da[1::2]
    lf, rf = np.fft.rfft(left), np.fft.rfft(right)
    lf, rf = np.roll(lf, shift), np.roll(rf, shift)
    lf[0:shift], rf[0:shift] = 0, 0

    nl, nr = np.fft.irfft(lf), np.fft.irfft(rf)
    ns = np.column_stack((nl, nr)).ravel().astype(np.float32)

    note1 = Note.Note(da, rate=w.getframerate(), channel=w.getnchannels(), decay=np.array([], dtype=np.float32))
    note2 = Note.Note(ns, rate=w.getframerate(), channel=w.getnchannels(), decay=np.array([], dtype=np.float32))

    player([note1, note2])


def resample_test2():
    w = wave.open(fs[-1], 'rb')
    da = np.array(wavdecode.from24le(w.readframes(w.getframerate()))).astype(np.float32)

    ns = wavdecode.pitchshift(da, w.getframerate(), 2, 1)

    note1 = Note.Note(da, rate=w.getframerate(), channel=w.getnchannels(), decay=np.array([], dtype=np.float32))
    note2 = Note.Note(ns, rate=w.getframerate(), channel=w.getnchannels(), decay=np.array([], dtype=np.float32))

    player([note1, note2])


def librosa_resample_test():
    sample, sr = librosa.load(fs[-1], mono=False, sr=SAMPLERATE, duration=1, res_type='polyphase')
    l = np.asfortranarray(sample[0])
    r = np.asfortranarray(sample[1])

    l = librosa.effects.pitch_shift(
        l, sr,
        n_steps=2.)
    r = librosa.effects.pitch_shift(
        r, sr,
        n_steps=2.)

    sample = np.column_stack((sample[0], sample[1])).ravel()
    sample *= 0x800000
    sample *= 0x100

    # resample, sr = sf.read(fs[0])
    # resample = resample.T
    resample = np.column_stack((l,r)).ravel()
    resample *= 0x800000
    resample *= 0x100

    note1 = Note.Note(sample, rate=sr, channel=CHANNELS, decay=decay)
    note2 = Note.Note(resample, rate=sr, channel=CHANNELS, decay=decay)
    note3 = Note.Note(resample, rate=sr, channel=CHANNELS, decay=decay)
    note4 = Note.Note(resample, rate=sr, channel=CHANNELS, decay=decay)

    player([note2, note3, note4])


def pydub_resample_test():
    sample = AudioSegment.from_wav(fs[-1])

    # shift the pitch up by half an octave (speed will increase proportionally)
    octaves = 0.5

    new_sample_rate = int(sample.frame_rate * (2.0 ** octaves))

    # keep the same samples but tell the computer they ought to be played at the
    # new, higher sample rate. This file sounds like a chipmunk but has a weird sample rate.
    hipitch_sound = sample._spawn(sample.raw_data, overrides={'frame_rate': new_sample_rate})

    # now we just convert it to a common sample rate (44.1k - standard audio CD) to
    # make sure it works in regular audio players. Other than potentially losing audio quality (if
    # you set it too low - 44.1k is plenty) this should now noticeable change how the audio sounds.
    hipitch_sound = hipitch_sound.set_frame_rate(48000)
    play(hipitch_sound)

    hipitch_sound = np.frombuffer(hipitch_sound.raw_data, dtype=np.int32)
    # hipitch_sound*= 0x100

    # note = Note.Note(hipitch_sound, rate=48000, channel=CHANNELS, decay=decay)
    # player([note])


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



# cProfile.run('f()')
# resample_test()
resample_test2()
# librosa_resample_test()
# pydub_resample_test()
# mix_test()
# librosa_mix_test()
# cProfile.run('mix_test()')
# cProfile.run('librosa_mix_test()')