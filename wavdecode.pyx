# cython: nonecheck=True
#        ^^^ Turns on nonecheck globally

import numpy as np
cimport numpy as np
cimport cython

ctypedef np.float_t DTYPE_t


@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
cdef np.int32_t to_sample(const unsigned char[:] bits):
    return (bits[2] << 24) | (bits[1] << 16) | (bits[0] << 8)

cdef bytes from_sample(np.uint32_t sample):
    return sample.to_bytes(4, byteorder='little')[1:]

@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def decay(const unsigned char[:] _bytes, np.ndarray[DTYPE_t, ndim=1] decay):
    cdef int v
    cdef bytearray d = bytearray(_bytes.shape[0])
    cdef int i = 0
    for i in range(0, _bytes.shape[0], 3):
        v = to_sample(_bytes[i:i+3])
        d[i:i+3] = from_sample(np.uint32(v*decay[i/3]))
    return d

@cython.boundscheck(False) # turn off bounds-checking for entire function
@cython.wraparound(False)  # turn off negative index wrapping for entire function
def mix(instruments, np.uint32_t frame_count, np.uint8_t channels, np.uint8_t width):
    cdef np.float_t v
    cdef int n = frame_count*channels*width
    cdef bytearray d = bytearray(n)
    frames = []
    for i in instruments:
        for f in list(i.playing.values())+list(i.ending.values()):
            frames.append(f.getframe(frame_count))

    #d = []
    for i in range(0, n, width):
        v = 0
        for f, e in frames:
            if len(f) > 4*i+3:
                s = to_sample(f[4*i:4*i+3])
                if len(e) > 0: s *= e[int(4*i/3)]
                v += s
        #print(from_sample(np.uint32(v)), bytes(np.uint32(v).data)[1:])
        #d[i:i+width] = from_sample(np.uint32(v))
        #d.append(np.int16(v))
        d[i:i+width] =  bytes(np.uint32(v).data)[1:]
    return d # np.array(d, dtype=np.int16)