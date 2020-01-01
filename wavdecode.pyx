# cython: boundscheck=False, wraparound=False, nonecheck=False

import numpy as np
cimport numpy as np
cimport cython

ctypedef np.float_t DTYPE_t


cdef int to_sample(const unsigned char[:] bits):
    return (bits[2] << 24) | (bits[1] << 16) | (bits[0] << 8)

cdef const unsigned char[:] from_sample(np.uint32_t sample):
    return sample.to_bytes(4, byteorder='little')[1:]

def decay(const unsigned char[:] _bytes, np.ndarray[DTYPE_t, ndim=1] decay):
    cdef int v
    cdef bytearray d = bytearray(_bytes.shape[0])
    cdef int i = 0
    for i in range(0, _bytes.shape[0], 3):
        v = to_sample(_bytes[i:i+3])
        d[i:i+3] = from_sample(np.uint32(v*decay[i/3]))
    return d

def mix(instruments, np.uint32_t frame_count, np.uint8_t channels, np.uint8_t width):
    cdef float v, s
    cdef short dec
    cdef short m = 4
    cdef unsigned int i, j, k, f, l
    cdef int n = frame_count*channels

    cdef const unsigned char[:] fr
    cdef double[:] de
    # cdef double[:] df = np.zeros(n)

    cdef bytearray d = bytearray(n)

    frames = []
    for inst in instruments:
        for note in list(inst.playing.values())+list(inst.ending.values()):
            fr, de = note.getframe(frame_count)
            frames.append((fr, de, len(fr), len(de)>0))

    f = len(frames)
    for i in range(n):
        # the current sample vaule
        v = 0

        # index for the samples, they are 24bit (two channel) arrays
        # with 192000 sampling, so skip over every 'm' sample
        k = width * m * i

        # loop over frames
        for j in range(f):
            fr, de, l, dec = frames[j]
            # check if the frame has data
            if l > k + width:
                # get the k'th sample, combine three bytes
                s = float(to_sample(fr[ k : k + width ]))
                # if decay array exists, use it
                if dec: s *= de[ int(k/width) ]
                # update the current sample value
                v += s

        # d[i:i+width] = bytes(np.uint32(v).data)[1:]
        # d  = from_sample(np.uint32(v))

        # store value
        # df[i] = v

        k = width * i
        d[k:k+width] = from_sample(np.uint32(v))

    #for i in range(n):
    #    k = width * i
    #    d[k:k+width] = from_sample(np.uint32(df[i]))

    return d