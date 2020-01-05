# cython: boundscheck=False, wraparound=False, nonecheck=False

# import librosa
import numpy as np
cimport numpy as np
cimport cython

cdef np.int32_t to_sample(const unsigned char[:] bits):
    return (bits[2] << 24) | (bits[1] << 16) | (bits[0] << 8)

cdef void from_sample(np.int32_t sample, unsigned char[:] d, np.uint32_t idx):
    d[idx] = (sample>>8)&0xff
    d[idx+1] = (sample>>16)&0xff
    d[idx+2] = (sample>>24)&0xff

cpdef np.int32_t[:] from24le(const unsigned char[:] _bytes):
    cdef np.uint32_t i, n = int(len(_bytes)/3)
    cdef np.int32_t[:] df = np.zeros(n).astype(np.int32)
    for i in range(n):
        df[i] = to_sample(_bytes[i*3:i*3+3])
    return df

cpdef unsigned char[:] to24le(const np.int32_t[:] df):
    cdef np.uint8_t width = 3
    cdef np.uint32_t i, k, n = len(df)

    cdef unsigned char[:] d = bytearray(n*width)

    for i in range(n):
        k = width * i
        from_sample(df[i], d, k)
    return d

cpdef np.float32_t[:] pitchshift(np.float32_t[:] samples, np.int32_t sr, np.int8_t shift, np.uint8_t fac):
    cdef np.float32_t[:] left = samples[0::2], right = samples[1::2]

    cdef np.float32_t octaves = shift/12.
    cdef np.int32_t new_sr = int(sr * (2.0 ** octaves))
    cdef np.float32_t ratio = new_sr/np.float(sr)

    cdef np.uint32_t i, x0, x1
    cdef np.float32_t x, y0l, y0r, y1l, y1r

    lr, rr = [], []
    for i in range(len(left)):
        x = i * ratio
        x0 = int(x)
        x1 = x0 + 1

        if x1 >= len(left): break

        y0l, y0r = left[x0], right[x0]
        y1l, y1r = left[x1], right[x1]
        lr.append(y0l + (x - x0) * (y1l - y0l)/(x1 - x0))
        rr.append(y0l + (x - x0) * (y1r - y0r)/(x1 - x0))

    return np.column_stack((lr[::fac], rr[::fac])).ravel().astype(np.float32)

def mix(list frames, np.uint32_t frame_count, np.uint8_t channels, np.uint8_t width, np.uint8_t shift):
    cdef np.float32_t v, s
    cdef np.uint8_t dec, c
    cdef np.uint32_t i, j, k, f, l, m, n = frame_count*channels

    cdef const unsigned char[:] frb = bytearray()
    cdef np.float32_t[:] fr = np.array([], dtype=np.float32)
    cdef np.float32_t[:] de = np.array([], dtype=np.float32)
    cdef np.float32_t[:] df = np.zeros(n, dtype=np.float32)

    cdef unsigned char[:] d = bytearray(n*width)

    f = len(frames)
    if f == 0: return d

    # loop over frames
    for j in range(f):
        _fr, de, l, dec, m = frames[j]

        _bytes = isinstance(_fr, bytes)
        if _bytes:
            frb = _fr
        else: fr = _fr


        # loop over l/r sample values
        for i from 0 <= i < n by channels:
            for c in range(channels):
                s = 0
                if _bytes:
                    # index for the samples, they are width-bit (two channel) arrays with rate of m*SAMPLERATE
                    k = width * m * i + width * c
                    # check if the frame has data
                    if l > k + width:
                        # get the k'th sample, combine three bytes
                        s = float(to_sample(frb[ k : k + width ]))

                else:
                    k = m * i + c
                    if l > k:
                        s = fr[k]

                # if decay array exists, use it
                if dec: s *= de[i + c]

                # update the current sample value
                df[i + c] += s

    for i in range(n):
        k = width * i
        # divide by 4 to prevent clipping
        from_sample(int(df[i]/4), d, k)

    return d
