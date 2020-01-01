# cython: boundscheck=False, wraparound=False, nonecheck=False

import struct
import numpy as np
cimport numpy as np
cimport cython

ctypedef np.float_t DTYPE_t

cdef int to_sample(const unsigned char[:] bits):
    return (bits[2] << 24) | (bits[1] << 16) | (bits[0] << 8)

cdef const unsigned char[:] from_sample(int sample):
    return struct.pack('i', int(sample))[1:]
    # return sample.to_bytes(3, byteorder='little', signed=True) # slower

def mix(frames, np.uint32_t frame_count, np.uint8_t channels, np.uint8_t width):
    cdef float v, s
    cdef short dec
    cdef short m = 4
    cdef unsigned int i, j, k, f, l
    cdef int n = frame_count*channels

    cdef const unsigned char[:] fr
    cdef double[:] de
    cdef double[:] df = np.zeros(n)

    cdef bytearray d = bytearray(n*width)

    f = len(frames)
    if f == 0: return d

    # loop over frames
    for j in range(f):
        fr, de, l, dec = frames[j]

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
                if dec: s *= de[ int(k/width) ]
                # update the current sample value
                df[i] += s

    for i in range(n):
        k = width * i
        d[k:k+width] = from_sample(int(df[i]))

    return d