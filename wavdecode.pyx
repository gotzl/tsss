# cython: boundscheck=False, wraparound=False, nonecheck=False

# import librosa
import numpy as np
cimport numpy as np
cimport cython

cdef int to_sample(const unsigned char[:] bits):
    return (bits[2] << 24) | (bits[1] << 16) | (bits[0] << 8)

cdef void from_sample(int sample, unsigned char[:] d, int idx):
    d[idx] = (sample>>8)&0xff
    d[idx+1] = (sample>>16)&0xff
    d[idx+2] = (sample>>24)&0xff

def mix(list frames, np.uint32_t frame_count, np.uint8_t channels, np.uint8_t width, short shift):
    cdef float v, s
    cdef short dec
    cdef unsigned int i, j, k, f, l, m
    cdef int n = frame_count*channels

    cdef const unsigned char[:] fr
    cdef double[:] de
    cdef double[:] df = np.zeros(n)

    cdef unsigned char[:] d = bytearray(n*width)

    f = len(frames)
    if f == 0: return d

    # loop over frames
    for j in range(f):
        fr, de, l, dec, m = frames[j]

        # loop over l/r sample values
        for i in range(n):

            # index for the samples, they are 24bit (two channel) arrays
            # with 192000 sampling, so skip over every 'm' sample
            k = width * m * i

            # check if the frame has data
            if l > k + width:
                # get the k'th sample, combine three bytes
                s = float(to_sample(fr[ k : k + width ]))

                # if decay array exists, use it
                if dec: s *= de[m * i]

                # update the current sample value
                df[i] += s

    #df = librosa.effects.pitch_shift(np.frombuffer(df, np.float), 1024, n_steps=4)
    if shift>0:
        left, right = df[0::2], df[1::2]
        lf, rf = np.fft.rfft(left), np.fft.rfft(right)
        lf, rf = np.roll(lf, shift), np.roll(rf, shift)
        lf[0:shift], rf[0:shift] = 0, 0
        nl, nr = np.fft.irfft(lf), np.fft.irfft(rf)
        df = np.column_stack((nl, nr)).ravel()

    for i in range(n):
        k = width * i
        # divide by 4 to prevent clipping
        from_sample(int(df[i]/4), d, k)

    return d
